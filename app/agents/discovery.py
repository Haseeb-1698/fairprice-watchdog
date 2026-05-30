"""
Discovery Agent (PRD agent #5).

Finds new operators / booking platforms to expand the monitoring set at RUNTIME,
using (in priority order):
  1. Brave Search API   — real human-readable URLs + snippets (primary)
  2. Firecrawl search   — structured search (if configured)
  3. Bright Data SERP    — raw Google SERP HTML (fallback)

Returns de-duplicated candidate sites the orchestrator queues scans against.
Self-contained: with no credentials it returns [] so the caller can use its
own last-resort safety net.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.services import brave_search, brightdata, firecrawl_client

logger = logging.getLogger(__name__)

# Hostnames that are aggregators / wikis / news, not bookable operators — we
# don't want to "scan" these for a checkout price, so they're filtered out of
# runtime discovery results.
_NON_OPERATOR_HOSTS = {
    "wikipedia.org", "reddit.com", "quora.com", "youtube.com", "facebook.com",
    "twitter.com", "x.com", "instagram.com", "tripadvisor.com", "yelp.com",
    "nytimes.com", "cnn.com", "forbes.com", "medium.com", "linkedin.com",
}

# Sectors most exposed to junk fees / drip pricing (PRD problem space).
DEFAULT_QUERIES = [
    "apartments for rent {city} application fee",
    "vacation rental {city} cleaning fee",
    "hotels {city} resort fee",
    "event tickets {city} service fee",
]


class DiscoveryAgent:
    name = "Discovery"

    def discover(self, query: str, limit: int = 10, country: str = "us") -> list[dict]:
        """Return [{title, url, source}] candidate operator sites for `query`,
        discovered live at runtime. Tries Brave → Firecrawl → Bright Data SERP."""
        candidates: list[dict] = []

        # 1. Brave Search — primary runtime source (real URLs + snippets).
        for item in brave_search.search(query, count=limit, country=country):
            candidates.append({
                "title": item.get("title", ""),
                "url": item["url"],
                "source": "brave",
            })

        # 2. Firecrawl search (if configured).
        if len(candidates) < limit:
            for item in firecrawl_client.search(query, limit=limit):
                url = item.get("url") if isinstance(item, dict) else None
                if url:
                    candidates.append({"title": item.get("title", ""), "url": url, "source": "firecrawl"})

        # 3. Bright Data SERP (raw HTML fallback).
        if len(candidates) < limit:
            for item in brightdata.serp_search(query, num=limit):
                url = item.get("url") if isinstance(item, dict) else None
                if url:
                    candidates.append({"title": item.get("title", ""), "url": url, "source": "brightdata_serp"})

        deduped = self._dedupe(candidates)
        logger.info("[Discovery] '%s' → %d candidate(s)", query, len(deduped))
        return deduped[:limit]

    def discover_sector(self, city: str, limit: int = 5) -> list[dict]:
        """Run the default sector queries for a city and merge results."""
        out: list[dict] = []
        for tmpl in DEFAULT_QUERIES:
            out.extend(self.discover(tmpl.format(city=city), limit=limit))
        return self._dedupe(out)

    @staticmethod
    def _dedupe(items: list[dict]) -> list[dict]:
        seen, out = set(), []
        for it in items:
            host = urlparse(it["url"]).netloc.lower().removeprefix("www.")
            if not host or host in seen:
                continue
            # Skip aggregators / wikis / news — not bookable operators.
            if any(host == h or host.endswith("." + h) for h in _NON_OPERATOR_HOSTS):
                continue
            seen.add(host)
            out.append(it)
        return out
