"""
firecrawl_client.py — Firecrawl integration (PRD: Crawler + Discovery agents).

Firecrawl turns a URL into clean, LLM-ready markdown/structured data without
custom spider logic. We use it for:
  • structured extraction of listing pages where state-level geo isn't required
  • the Discovery agent (finding/normalizing new operator sites)

For the geo-price demo the page must be fetched *through a Bright Data state
proxy* (Firecrawl scrapes from its own infra and can't honor our residential
exit), so the Crawler fetches geo-HTML via Bright Data and may use Firecrawl as
a cross-check / clean-extraction layer. Lazy + optional: returns None if the
client or API key is absent, so nothing breaks in mock mode.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def available() -> bool:
    return bool(settings.FIRECRAWL_API_KEY)


def scrape_markdown(url: str) -> Optional[str]:
    """Return clean markdown for a URL via Firecrawl, or None if unavailable."""
    if not available():
        return None
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY, api_url=settings.FIRECRAWL_API_URL)
        result = app.scrape_url(url, params={"formats": ["markdown"]})
        # firecrawl-py returns a dict-like; tolerate both shapes across versions.
        if isinstance(result, dict):
            return result.get("markdown") or (result.get("data") or {}).get("markdown")
        return getattr(result, "markdown", None)
    except Exception as e:
        logger.warning("Firecrawl scrape failed for %s: %s", url, e)
        return None


def search(query: str, limit: int = 10) -> list[dict]:
    """Discovery: find operator/listing sites for a query. Empty list if unavailable."""
    if not available():
        return []
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY, api_url=settings.FIRECRAWL_API_URL)
        result = app.search(query, params={"limit": limit})
        data = result.get("data", result) if isinstance(result, dict) else result
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("Firecrawl search failed for '%s': %s", query, e)
        return []
