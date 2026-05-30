"""
web_search.py — web search provider for the Discovery agent.

Returns real, human-readable URLs + text snippets so the Discovery agent can
find live target sites at runtime. Used as the primary discovery source ahead
of Firecrawl and raw SERP fetching.

Self-contained: returns [] when no key is configured so the caller can fall
back to its own targets and the pipeline never hard-fails.
"""
from __future__ import annotations

import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def is_live() -> bool:
    return bool(getattr(settings, "WEB_SEARCH_API_KEY", ""))


def search(query: str, count: int = 10, country: str = "us", timeout: int = 15) -> list[dict]:
    """
    Run a web search. Returns a list of {title, url, description, source}.

    Args:
        query:   the search query
        count:   max results (capped at 20)
        country: 2-letter country bias (us/gb/de/...) — matches our geo coverage
    """
    if not is_live():
        logger.info("[WebSearch] no API key — skipping (caller falls back)")
        return []

    try:
        resp = requests.get(
            _ENDPOINT,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": settings.WEB_SEARCH_API_KEY,
            },
            params={
                "q": query,
                "count": min(max(count, 1), 20),
                "country": (country or "us").lower(),
                "safesearch": "off",
                "text_decorations": False,
            },
            timeout=(10, timeout),
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("[WebSearch] search failed for '%s': %s", query, e)
        return []

    results: list[dict] = []
    for r in (data.get("web", {}) or {}).get("results", []) or []:
        url = r.get("url")
        if not url:
            continue
        results.append({
            "title": r.get("title", "") or url,
            "url": url,
            "description": r.get("description", "") or "",
            "source": "web_search",
        })
    logger.info("[WebSearch] '%s' → %d result(s)", query, len(results))
    return results
