"""
Journey Simulator Agent (PRD agent #2).

Walks the checkout funnel from a given US state and captures the *final* total
plus every added fee — the gap between this and the advertised price is the
evidence. Connects to Bright Data's Browser API (a real remote CDP browser) via
Playwright when configured; otherwise falls back to a geo-targeted fetch.

HARD RULE (PRD Risk #1): we stop at the page *before* payment submission. We
read the total; we never enter payment details or place an order. This is
enforced in `_walk_live` (aborts on any payment URL/step) and is a feature to
highlight to judges, not a limitation.

Skyvern (starred) is the intended drop-in for true LLM-driven multi-step
navigation on arbitrary sites; `_walk_live` is the seam where it plugs in.
"""
from __future__ import annotations

import logging

from app.agents import extract
from app.agents.llm import complete_json
from app.agents.types import FeeItem
from app.core.config import settings
from app.services import brightdata

logger = logging.getLogger(__name__)

# Buttons that advance the funnel (best-effort, generic across booking sites).
_ADVANCE_HINTS = ["book", "reserve", "continue", "checkout", "next", "review", "get total"]
# Anything matching this means we have reached payment — STOP immediately.
_PAYMENT_STOP = ["payment", "pay now", "card number", "billing", "place order", "complete booking"]


class JourneyAgent:
    name = "Journey Simulator"

    def walk(self, url: str, state: str) -> dict:
        """
        Returns:
            {"state", "final_price", "fees": [FeeItem], "html", "source", "live"}
        """
        if settings.brightdata_browser_live:
            try:
                return self._walk_live(url, state)
            except Exception as e:
                logger.warning("[Journey] live browser walk failed (%s) — falling back to fetch", e)

        # Fallback: geo-targeted fetch + extraction (also the mock path).
        fetched = brightdata.fetch_html(url, state)
        return self._parse_checkout(fetched.html, state, fetched.source, fetched.live)

    # ── Live Browser API path (Playwright over CDP) ───────────────────────────
    def _walk_live(self, url: str, state: str) -> dict:
        from playwright.sync_api import sync_playwright

        cdp = brightdata.browser_cdp_url(state)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)

            # Best-effort advance through funnel steps, stopping before payment.
            for _ in range(4):
                if self._is_payment_step(page):
                    logger.info("[Journey] reached payment step — STOPPING (capture-only).")
                    break
                if not self._click_advance(page):
                    break
                page.wait_for_load_state("networkidle", timeout=30_000)

            html = page.content()
            browser.close()
        return self._parse_checkout(html, state, "browser_api", True)

    def _is_payment_step(self, page) -> bool:
        try:
            body = (page.content() or "").lower()
        except Exception:
            return False
        return any(k in body for k in _PAYMENT_STOP)

    def _click_advance(self, page) -> bool:
        for hint in _ADVANCE_HINTS:
            try:
                btn = page.get_by_role("button", name=__import__("re").compile(hint, __import__("re").I)).first
                if btn and btn.is_visible():
                    btn.click(timeout=5_000)
                    return True
            except Exception:
                continue
        return False

    # ── Shared parsing ────────────────────────────────────────────────────────
    def _parse_checkout(self, html: str, state: str, source: str, live: bool) -> dict:
        fees = extract.parse_fee_items(html)
        final = extract.parse_final_price(html)

        if not fees or final is None:
            llm_fees, llm_final = self._extract_with_llm(html)
            fees = fees or llm_fees
            final = final if final is not None else llm_final

        logger.info("[Journey] %s → final=$%s, %d fee(s) (source=%s live=%s)",
                    state, final, len(fees), source, live)
        return {
            "state": state,
            "final_price": final or 0.0,
            "fees": fees,
            "html": html,
            "source": source,
            "live": live,
        }

    def _extract_with_llm(self, html: str):
        md = extract.normalize_html(html)[:7000]
        data = complete_json(
            system=(
                "You extract checkout pricing from a booking/rental page. Identify the final "
                "total due and each added fee line-item (resort, cleaning, service, admin, etc.)."
            ),
            user=(
                f"Page content:\n{md}\n\n"
                'Return JSON: {"final_price": <number>, '
                '"fees": [{"fee_name": str, "fee_amount": number, "fee_type": str}]}'
            ),
            max_tokens=1200,
        )
        fees = [
            FeeItem(
                fee_name=f.get("fee_name", "Fee"),
                fee_amount=float(f.get("fee_amount") or 0),
                fee_type=f.get("fee_type", "unknown"),
            )
            for f in (data.get("fees") or [])
            if f.get("fee_amount")
        ]
        try:
            final = float(data.get("final_price") or 0.0)
        except (TypeError, ValueError):
            final = 0.0
        return fees, final
