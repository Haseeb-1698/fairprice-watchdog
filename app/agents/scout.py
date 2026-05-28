"""
Scout Agent — quick-test candidate URLs before committing to the full pipeline.

Fetches a page via Bright Data (same path as Crawler) then runs lightweight
heuristics: blocked? price content? fee keywords? Returns a score so the
hunt orchestrator can filter dead targets before wasting pipeline time.

Mock-safe: fetch_html() returns mock HTML with data-attrs for prices and fees,
so the scout scores them high — the demo works fully offline.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.services import brightdata

logger = logging.getLogger(__name__)

_BLOCK_TOKENS = [
    "cloudflare", "attention required", "captcha", "access denied",
    "enable javascript", "unusual traffic", "just a moment",
    "checking your browser", "verify you are human",
]

_FEE_KEYWORDS = [
    "resort fee", "destination fee", "amenity fee", "service fee",
    "cleaning fee", "admin fee", "application fee", "facility fee",
    "booking fee", "convenience fee", "surcharge", "processing fee",
    "mandatory charge",
]

_PRICE_RE = re.compile(r"\$\s?\d{2,6}(?:\.\d{2})?")


@dataclass
class ScoutResult:
    url: str
    title: str
    reachable: bool
    blocked: bool
    has_prices: bool
    has_fee_keywords: bool
    score: float           # 0.0–1.0
    source: str            # "live" | "mock" | "error"


class ScoutAgent:
    name = "Scout"

    def probe(self, url: str, state: str = "CA", title: str = "") -> ScoutResult:
        """Quick fetch + heuristic check."""
        try:
            fetched = brightdata.fetch_html(url, state, timeout=30)
        except Exception as e:
            logger.warning("[Scout] fetch failed for %s: %s", url, e)
            return ScoutResult(
                url=url, title=title, reachable=False, blocked=False,
                has_prices=False, has_fee_keywords=False, score=0.0,
                source="error",
            )

        html_lower = fetched.html.lower()
        reachable = fetched.status_code == 200 and len(fetched.html) > 500
        blocked = self._detect_blocking(html_lower)
        has_prices = self._detect_prices(html_lower)
        has_fee_keywords = self._detect_fee_keywords(html_lower)
        score = self._score(reachable, blocked, has_prices, has_fee_keywords)
        source = "mock" if fetched.source == "mock" else "live"

        logger.info(
            "[Scout] %s → reachable=%s blocked=%s prices=%s fees=%s score=%.2f (%s)",
            url, reachable, blocked, has_prices, has_fee_keywords, score, source,
        )
        return ScoutResult(
            url=url, title=title, reachable=reachable, blocked=blocked,
            has_prices=has_prices, has_fee_keywords=has_fee_keywords,
            score=score, source=source,
        )

    @staticmethod
    def _detect_blocking(html: str) -> bool:
        return any(tok in html for tok in _BLOCK_TOKENS)

    @staticmethod
    def _detect_prices(html: str) -> bool:
        return bool(_PRICE_RE.search(html))

    @staticmethod
    def _detect_fee_keywords(html: str) -> bool:
        return any(kw in html for kw in _FEE_KEYWORDS)

    @staticmethod
    def _score(reachable: bool, blocked: bool, has_prices: bool, has_fee_keywords: bool) -> float:
        s = 0.0
        if reachable:
            s += 0.3
        if not blocked:
            s += 0.2
        if has_prices:
            s += 0.3
        if has_fee_keywords:
            s += 0.2
        return round(s, 2)
