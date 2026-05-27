"""
Discovery Agent (PRD agent #5).

Finds new operators / booking platforms to expand the monitoring set, using
Bright Data's SERP API and Firecrawl search. Returns de-duplicated candidate
sites; the orchestrator can then queue scans against them.

Self-contained: with no credentials it returns mock candidates so the pipeline
and demo flow stay intact.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.services import brightdata, firecrawl_client

logger = logging.getLogger(__name__)

# Sectors most exposed to junk fees / drip pricing (PRD problem space).
DEFAULT_QUERIES = [
    "apartments for rent {city} application fee",
    "vacation rental {city} cleaning fee",
    "hotels {city} resort fee",
    "event tickets {city} service fee",
]


class DiscoveryAgent:
    name = "Discovery"

    def discover(self, query: str, limit: int = 10) -> list[dict]:
        """Return [{title, url, source}] candidate operator sites for `query`."""
        candidates: list[dict] = []

        for item in firecrawl_client.search(query, limit=limit):
            url = item.get("url") if isinstance(item, dict) else None
            if url:
                candidates.append({"title": item.get("title", ""), "url": url, "source": "firecrawl"})

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
            if host and host not in seen:
                seen.add(host)
                out.append(it)
        return out
