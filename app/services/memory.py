"""
memory.py — cross-scan operator memory.

After each scan we remember what fee patterns an operator (domain) exhibited.
On a later scan of the same operator the agents can recall "we've seen this
operator hide a resort fee + service fee before" — turning one-off scans into
a growing intelligence base (the Discovery/Filing agents' long-term memory).

Two layers:
  • Local JSON store (primary)  — fast, reliable, always available. Drives the
    recall shown in the studio feed + results.
  • Knowledge-graph enrichment (background) — a richer semantic graph built in a
    daemon thread AFTER the scan completes, so it can never block or break a
    live scan. Degrades silently if the graph backend isn't configured.

Public surface:
    record(domain, observation)      — fire-and-forget; persists + schedules graph enrich
    recall(domain) -> dict | None    — prior observations for a domain
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_STORE = Path(os.environ.get("MEMORY_STORE_DIR", "./memory_store"))
_STORE_FILE = _STORE / "operators.json"
_lock = threading.Lock()


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.") or url
    except Exception:
        return url


def _load() -> dict:
    try:
        if _STORE_FILE.exists():
            return json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(data: dict) -> None:
    try:
        _STORE.mkdir(parents=True, exist_ok=True)
        _STORE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("memory save failed: %s", e)


def recall(domain: str) -> Optional[dict]:
    """Return the most recent observation we have for `domain`, or None."""
    with _lock:
        rec = _load().get(domain)
    return rec


def record(domain: str, observation: dict) -> None:
    """Persist an observation for `domain` (local store) and schedule a
    background knowledge-graph enrichment. Never raises."""
    try:
        with _lock:
            data = _load()
            prev = data.get(domain, {})
            data[domain] = {
                "domain": domain,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "scan_count": int(prev.get("scan_count", 0)) + 1,
                "fee_types": sorted(set(prev.get("fee_types", []) + observation.get("fee_types", []))),
                "max_geo_gap": max(float(prev.get("max_geo_gap", 0)), float(observation.get("geo_gap", 0))),
                "last_summary": observation.get("summary", ""),
            }
            _save(data)
    except Exception as e:
        logger.debug("memory record failed: %s", e)

    # Background graph enrichment — fully detached, best-effort.
    t = threading.Thread(target=_enrich_graph, args=(domain, observation), daemon=True)
    t.start()


def _enrich_graph(domain: str, observation: dict) -> None:
    """Feed the observation into the knowledge graph. Runs in a daemon thread
    so slowness/failure can't affect the scan. No-op if backend unavailable."""
    try:
        import cognee  # heavy optional dep
        import asyncio

        text = (
            f"Operator {domain} was scanned by FairPrice Watchdog. "
            f"Fee types observed: {', '.join(observation.get('fee_types', [])) or 'none'}. "
            f"Geographic price gap: {observation.get('geo_gap', 0)}. "
            f"Summary: {observation.get('summary', '')}."
        )

        async def _run():
            await cognee.add(text, dataset_name="fairprice_operators")
            await cognee.cognify()

        asyncio.run(_run())
        logger.info("[Memory] knowledge graph enriched for %s", domain)
    except ImportError:
        logger.debug("[Memory] cognee not installed — graph enrichment skipped")
    except Exception as e:
        logger.debug("[Memory] graph enrichment failed for %s: %s", domain, e)
