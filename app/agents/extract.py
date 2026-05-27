"""
extract.py — HTML → structured data helpers shared by the agents.

Strategy (robust to both mock and live pages):
  1. Prefer machine-readable data-* attributes (present on our mock pages and
     easy to inject on instrumented captures).
  2. Fall back to regex over the rendered text for $ amounts.
  3. Normalize HTML → markdown (via markitdown when installed) before handing a
     page to the LLM, which keeps token cost down and parsing reliable.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.agents.types import FeeItem

logger = logging.getLogger(__name__)

_PRICE_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")


def _to_float(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def normalize_html(html: str) -> str:
    """HTML → clean markdown for LLM consumption. Falls back to a tag strip."""
    try:
        from markitdown import MarkItDown
        import io
        md = MarkItDown()
        result = md.convert_stream(io.BytesIO(html.encode("utf-8")), file_extension=".html")
        return (result.text_content or "").strip()
    except Exception:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()


def parse_advertised_price(html: str) -> Optional[float]:
    m = re.search(r'data-advertised-price="([0-9.]+)"', html)
    if m:
        return _to_float(m.group(1))
    # Heuristic: first price near the word "advertised" or the first price seen.
    near = re.search(r'(?is)advertised[^$]{0,40}\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)', html)
    if near:
        return _to_float(near.group(1))
    prices = find_prices(html)
    return prices[0] if prices else None


def parse_final_price(html: str) -> Optional[float]:
    m = re.search(r'data-final-price="([0-9.]+)"', html)
    if m:
        return _to_float(m.group(1))
    near = re.search(r'(?is)(total|due today|grand total)[^$]{0,40}\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)', html)
    if near:
        return _to_float(near.group(2))
    prices = find_prices(html)
    return max(prices) if prices else None


def parse_fee_items(html: str) -> list[FeeItem]:
    """Extract fees from data-fee-* attributes (instrumented/mock captures)."""
    fees: list[FeeItem] = []
    for m in re.finditer(
        r'data-fee-name="([^"]+)"\s+data-fee-type="([^"]*)"\s+data-fee-amount="([0-9.]+)"', html
    ):
        amt = _to_float(m.group(3))
        if amt is not None:
            fees.append(FeeItem(fee_name=m.group(1), fee_amount=amt, fee_type=m.group(2) or "unknown"))
    return fees


def find_prices(text: str) -> list[float]:
    out = []
    for m in _PRICE_RE.finditer(text):
        v = _to_float(m.group(1))
        if v is not None:
            out.append(v)
    return out
