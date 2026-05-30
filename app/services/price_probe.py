"""
price_probe.py — fast geo price-discrimination probe.

Runs the SAME product query through a geo-biased web search for several
countries and extracts the prices each country's shopper is shown. When the
prices differ, that's price discrimination by viewer location — demonstrated
in ~3 seconds without running the full scan pipeline.

This is the fast pre-check companion to the deep scan: search reveals WHICH
operators/products discriminate, the scan then proves it with sealed evidence.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.services import web_search

logger = logging.getLogger(__name__)

# Country bias → display label + currency hint.
DEFAULT_COUNTRIES = [
    {"code": "us", "label": "United States", "flag": "🇺🇸"},
    {"code": "gb", "label": "United Kingdom", "flag": "🇬🇧"},
    {"code": "de", "label": "Germany", "flag": "🇩🇪"},
]

_PRICE_RE = re.compile(
    r"(?:[\$£€]\s?\d+(?:[.,]\d{1,2})?)|(?:\d+(?:[.,]\d{1,2})?\s?(?:USD|EUR|GBP))"
)


def _extract_prices(text: str, limit: int = 6) -> list[str]:
    seen, out = set(), []
    for m in _PRICE_RE.findall(text or ""):
        v = m.strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
        if len(out) >= limit:
            break
    return out


def probe(query: str, countries: Optional[list[dict]] = None, per_country: int = 4) -> dict:
    """
    For each country, run a geo-biased search and collect the prices shown.
    Returns {query, results: [{code,label,flag,prices,top_url,top_title}], discrimination}.
    """
    countries = countries or DEFAULT_COUNTRIES
    results = []
    for c in countries:
        hits = web_search.search(query, count=per_country, country=c["code"])
        prices: list[str] = []
        for h in hits:
            prices += _extract_prices(f"{h.get('title','')} {h.get('description','')}")
        # de-dup preserving order
        seen, dedup = set(), []
        for p in prices:
            if p not in seen:
                seen.add(p); dedup.append(p)
        results.append({
            "code": c["code"],
            "label": c["label"],
            "flag": c.get("flag", ""),
            "prices": dedup[:6],
            "top_url": hits[0]["url"] if hits else "",
            "top_title": hits[0]["title"] if hits else "",
        })

    # Heuristic: discrimination if the price sets differ across countries.
    price_sets = [tuple(r["prices"]) for r in results if r["prices"]]
    discrimination = len(set(price_sets)) > 1 and len(price_sets) >= 2

    return {
        "query": query,
        "results": results,
        "discrimination": discrimination,
    }
