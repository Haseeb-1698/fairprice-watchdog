"""
vision.py — read prices off a RENDERED screenshot with a vision LLM.

The Web Unlocker's screenshot mode returns a fully-rendered page (JavaScript
has already executed), so prices that are injected by JS — invisible in the raw
HTML — are visible in the image. A vision model reads them the way a human
would. This is the fallback when HTML/regex/text extraction yields nothing
(modern travel + retail sites render prices client-side).

Uses the OpenAI-compatible vision endpoint (AIMLAPI gpt-4o). Returns {} on any
failure so the caller falls back cleanly.
"""
from __future__ import annotations

import base64
import json
import logging
import re

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

_VISION_MODEL = "gpt-4o"

_PROMPT = (
    "This is a screenshot of a product, hotel, or checkout page. Extract the pricing.\n"
    "Return ONLY JSON: {\"advertised_price\": <number or 0>, \"final_price\": <number or 0>, "
    "\"currency\": \"<symbol or code>\", \"fees\": [{\"fee_name\": \"...\", \"fee_amount\": <number>}]}.\n"
    "advertised_price = the headline/nightly/list price shown most prominently. "
    "final_price = the total/checkout price if shown, else same as advertised. "
    "fees = any itemized add-ons (resort fee, cleaning, service, tax). Numbers only, no symbols."
)


def is_available() -> bool:
    return bool(getattr(settings, "AIMLAPI_KEY", "") or getattr(settings, "OPENAI_API_KEY", ""))


def _endpoint_and_key() -> tuple[str, str, str]:
    if getattr(settings, "AIMLAPI_KEY", ""):
        return settings.AIMLAPI_ENDPOINT, settings.AIMLAPI_KEY, settings.AIMLAPI_MODEL or _VISION_MODEL
    return "https://api.openai.com/v1", settings.OPENAI_API_KEY, "gpt-4o"


def extract_prices(image_bytes: bytes, timeout: int = 60) -> dict:
    """Vision-extract pricing from a rendered screenshot. Returns a dict with
    advertised_price / final_price / currency / fees, or {} on failure."""
    if not is_available() or not image_bytes:
        return {}
    endpoint, key, model = _endpoint_and_key()
    b64 = base64.b64encode(image_bytes).decode()
    body = {
        "model": model,
        "max_tokens": 600,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    }
    try:
        r = requests.post(
            f"{endpoint.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body, timeout=(15, timeout),
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("[Vision] extraction failed: %s", e)
        return {}

    # Parse JSON (tolerate ```json fences / prose).
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except Exception:
        return {}
    logger.info("[Vision] extracted: advertised=%s final=%s fees=%s",
                data.get("advertised_price"), data.get("final_price"), len(data.get("fees", [])))
    return data
