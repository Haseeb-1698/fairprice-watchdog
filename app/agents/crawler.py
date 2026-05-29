"""
Crawler Agent (PRD agent #1).

Loads a listing as a real user located in a specific US state, using Bright Data
geo-targeted residential proxies. Its job in the two-geo demo is narrow and
reliable: fetch the listing page from `state` and read the *advertised* price.

(The starred Firecrawl integration would slot in here for clean structured
extraction on messy live pages — see `_extract_advertised`. For the demo we use
deterministic data-attr/regex parsing with an LLM fallback so it never stalls.)
"""
from __future__ import annotations

import logging

from app.agents import extract
from app.agents.llm import complete_json
from app.services import brightdata, firecrawl_client

logger = logging.getLogger(__name__)


class CrawlerAgent:
    name = "Crawler"

    def load(self, url: str, state: str, scan_id: str | None = None) -> dict:
        """
        Returns:
            {"state", "advertised_price", "html", "source", "live"}
        """
        fetched = brightdata.fetch_html(url, state, scan_id=scan_id)
        advertised = extract.parse_advertised_price(fetched.html)

        if advertised is None:
            advertised = self._extract_advertised(fetched.html, url)

        logger.info(
            "[Crawler] %s @ %s → advertised=$%s (source=%s live=%s)",
            url, state, advertised, fetched.source, fetched.live,
        )
        return {
            "state": state,
            "advertised_price": advertised or 0.0,
            "html": fetched.html,
            "source": fetched.source,
            "live": fetched.live,
        }

    def _extract_advertised(self, html: str, url: str = "") -> float:
        """LLM fallback: read the headline/advertised price off the page.
        Prefers Firecrawl's clean markdown when available, else markitdown."""
        md = (firecrawl_client.scrape_markdown(url) if url else None) or extract.normalize_html(html)
        md = md[:6000]
        data = complete_json(
            system="You extract the single advertised/headline price from a listing page.",
            user=f"Page content:\n{md}\n\nReturn JSON: {{\"advertised_price\": <number>}}",
            max_tokens=200,
        )
        try:
            return float(data.get("advertised_price") or 0.0)
        except (TypeError, ValueError):
            return 0.0
