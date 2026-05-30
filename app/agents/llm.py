"""
llm.py — provider-agnostic LLM client with a fallback chain.

Ported from the Fathom orchestrator's multi-provider pattern. Order is driven
by settings.LLM_PROVIDER ("auto" tries each configured provider in turn):

    anthropic (Claude Opus 4.7)  →  azure_kimi  →  openai  →  mock

`complete()` returns text. `complete_json()` returns a parsed dict and is what
the Diff / Law-Mapper agents use for structured fee classification. When no
provider is configured it returns a deterministic mock so the pipeline runs
offline — the mock is fee-aware so the demo still produces sensible labels.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


def _providers_in_order() -> list[str]:
    pref = (settings.LLM_PROVIDER or "auto").lower()
    chain = []
    if settings.ANTHROPIC_API_KEY:
        chain.append("anthropic")
    if settings.KIMI_API_KEY:
        chain.append("kimi")
    if settings.AZURE_KIMI_ENDPOINT and settings.AZURE_KIMI_KEY:
        chain.append("azure_kimi")
    if settings.OPENAI_API_KEY:
        chain.append("openai")
    if getattr(settings, "AIMLAPI_KEY", ""):
        chain.append("aimlapi")
    chain.append("mock")
    if pref != "auto":
        # Pin the preferred provider first, keep the rest as fallback.
        chain = [pref] + [c for c in chain if c != pref]
    return chain


# ── Per-provider callers ──────────────────────────────────────────────────────

def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text").strip()


def _call_openai_compatible(endpoint: str, key: str, model: str, system: str, user: str,
                            max_tokens: int, temperature: float) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    for attempt in range(3):
        r = requests.post(
            f"{endpoint.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=(15, 60),
        )
        if r.status_code == 429:
            time.sleep(2 ** attempt * 3)
            continue
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        return (msg.get("content") or msg.get("reasoning_content") or "").strip()
    raise RuntimeError("rate limited after retries")


def _call_kimi(system: str, user: str, max_tokens: int) -> str:
    # Direct Moonshot/Kimi platform — OpenAI-compatible, temperature must be 1.
    return _call_openai_compatible(
        settings.KIMI_ENDPOINT, settings.KIMI_API_KEY, settings.KIMI_MODEL,
        system, user, max_tokens, temperature=1.0,
    )


def _call_azure_kimi(system: str, user: str, max_tokens: int) -> str:
    # Azure Kimi only accepts temperature=1.
    return _call_openai_compatible(
        settings.AZURE_KIMI_ENDPOINT, settings.AZURE_KIMI_KEY, settings.AZURE_KIMI_MODEL,
        system, user, max_tokens, temperature=1.0,
    )


def _call_openai(system: str, user: str, max_tokens: int) -> str:
    return _call_openai_compatible(
        "https://api.openai.com/v1", settings.OPENAI_API_KEY, settings.OPENAI_MODEL,
        system, user, max_tokens, temperature=0.1,
    )


def _call_aimlapi(system: str, user: str, max_tokens: int) -> str:
    # OpenAI-compatible multi-model gateway — resilient fallback if the primary
    # LLM is rate-limited (gives the pipeline a second independent provider).
    return _call_openai_compatible(
        settings.AIMLAPI_ENDPOINT, settings.AIMLAPI_KEY, settings.AIMLAPI_MODEL,
        system, user, max_tokens, temperature=0.1,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def complete(system: str, user: str, max_tokens: int = 1500) -> str:
    """Run the prompt through the provider fallback chain. Always returns text."""
    last_err: Optional[Exception] = None
    for provider in _providers_in_order():
        try:
            if provider == "anthropic":
                return _call_anthropic(system, user, max_tokens)
            if provider == "kimi":
                return _call_kimi(system, user, max_tokens)
            if provider == "azure_kimi":
                return _call_azure_kimi(system, user, max_tokens)
            if provider == "openai":
                return _call_openai(system, user, max_tokens)
            if provider == "aimlapi":
                return _call_aimlapi(system, user, max_tokens)
            if provider == "mock":
                return _mock_complete(system, user)
        except Exception as e:
            last_err = e
            logger.warning("LLM provider '%s' failed (%s) — trying next", provider, e)
    logger.error("All LLM providers failed: %s", last_err)
    return _mock_complete(system, user)


def complete_json(system: str, user: str, max_tokens: int = 2000) -> dict:
    """
    Like complete(), but instructs the model to return JSON and parses it.
    Tolerates ```json fences and leading prose.
    """
    sys2 = system + "\n\nReturn ONLY valid JSON. No prose, no markdown fences."
    raw = complete(sys2, user, max_tokens)
    return _extract_json(raw)


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    candidate = fence.group(1) if fence else text
    # Fall back to the first {...} block.
    if not fence:
        brace = re.search(r"\{[\s\S]*\}", candidate)
        if brace:
            candidate = brace.group(0)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        logger.warning("LLM did not return parseable JSON; got: %.200s", text)
        return {}


# ── Mock (offline, fee-aware) ─────────────────────────────────────────────────

def _mock_complete(system: str, user: str) -> str:
    """
    Deterministic offline response. For the Diff/Law-Mapper JSON prompts it
    classifies common drip-fee names so the demo still flags junk fees sensibly.
    """
    lower = (system + user).lower()
    if "json" in lower and "fee" in lower:
        fees = []
        catalog = {
            "resort": ("FTC 16 CFR Part 464 — Unfair or Deceptive Fees (mandatory fee not in advertised price)", True),
            "cleaning": ("FTC 16 CFR Part 464 — drip pricing of mandatory ancillary charge", True),
            "admin": ("FTC 16 CFR Part 464 — undisclosed mandatory administrative fee", True),
            "application": ("FTC 16 CFR Part 464 — undisclosed mandatory fee", True),
            "service": ("FTC 16 CFR Part 464 — mandatory service charge omitted from advertised total", True),
            "tax": ("Government-imposed tax (generally permissible if disclosed)", False),
        }
        names = (
            re.findall(r'data-fee-name="([^"]+)"', user)
            or re.findall(r"""['"]fee_name['"]?\s*:\s*['"]([^'"]+)['"]""", user)
            or re.findall(r'"([^"]*fee[^"]*)"', user, re.I)
        )
        for name in names:
            key = next((k for k in catalog if k in name.lower()), None)
            clause, junk = catalog.get(key, ("Requires manual review", False))
            fees.append({"fee_name": name, "is_junk_fee": junk, "ftc_clause": clause})
        return json.dumps({"fees": fees, "summary": "[mock] classified by FairPrice offline heuristic"})
    return "[mock LLM response — no provider configured]"
