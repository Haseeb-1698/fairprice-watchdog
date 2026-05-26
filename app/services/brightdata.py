"""
brightdata.py — Bright Data integration for FairPrice Watchdog.

Provides the agents with geo-targeted web access:

  • proxy_for_state(state)  → US state-targeted residential proxy (the demo core)
  • fetch_html(url, state)  → page HTML via Web Unlocker / residential proxy
  • browser_cdp_url(state)  → drivable CDP endpoint (Browser API) for Journey Sim
  • serp_search(query)      → SERP API results (Discovery agent — stub for now)

Design mirrors storage/minio_client.py: every call degrades gracefully. When
credentials are absent (settings.brightdata_live is False) it returns
deterministic MOCK data so the whole pipeline runs offline with zero credits —
and the mock deliberately varies price by state so the two-geo split is visible
in a demo without any live calls.
"""
from __future__ import annotations

import hashlib
import logging
import urllib3
from dataclasses import dataclass, field
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Bright Data terminates TLS with its own CA on the superproxy; suppress the
# verify=False noise (we are not asserting cert identity on the proxy hop).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class FetchResult:
    """Result of a geo-targeted page fetch."""
    url: str
    state: str
    html: str
    status_code: int
    live: bool                       # True if served by Bright Data, False if mock
    source: str                      # "web_unlocker" | "residential" | "mock"
    bytes: int = field(default=0)

    def __post_init__(self):
        self.bytes = len(self.html.encode("utf-8", errors="ignore"))


# ── Proxy construction ────────────────────────────────────────────────────────

def proxy_username(state: str, zone: Optional[str] = None) -> str:
    """
    Build a Bright Data proxy username with US state geo-targeting.

    Format: brd-customer-<id>-zone-<zone>-country-us-state-<st>
    The `-state-<st>` segment is what makes the same listing resolve to a
    different price by location — the heart of the geo-discrimination proof.
    """
    zone = zone or settings.BRIGHTDATA_ZONE
    st = (state or "").strip().lower()
    user = f"brd-customer-{settings.BRIGHTDATA_CUSTOMER_ID}-zone-{zone}-country-us"
    if st:
        user += f"-state-{st}"
    return user


def proxy_for_state(state: str) -> dict[str, str]:
    """Return a requests-style proxies dict for the residential zone in `state`."""
    user = proxy_username(state)
    pwd = settings.BRIGHTDATA_ZONE_PASSWORD
    host = settings.BRIGHTDATA_PROXY_HOST
    port = settings.BRIGHTDATA_PROXY_PORT
    proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}


def browser_cdp_url(state: str) -> Optional[str]:
    """
    Return the Bright Data Browser API CDP websocket URL for `state`.

    Journey Simulator (Skyvern / Playwright) connects to this to drive a real
    remote browser through the checkout funnel. Returns None in mock mode.
    """
    if not settings.brightdata_browser_live:
        return None
    user = proxy_username(state, zone=settings.BRIGHTDATA_BROWSER_ZONE)
    pwd = settings.BRIGHTDATA_BROWSER_PASSWORD
    host = settings.BRIGHTDATA_BROWSER_HOST
    port = settings.BRIGHTDATA_BROWSER_PORT
    return f"wss://{user}:{pwd}@{host}:{port}"


# ── Page fetch (Crawler) ──────────────────────────────────────────────────────

def fetch_html(url: str, state: str, timeout: int = 60) -> FetchResult:
    """
    Fetch fully-rendered HTML for `url` as a real user in `state`.

    Live path: route through the Bright Data residential proxy (which fronts the
    Web Unlocker for anti-bot bypass). Mock path: synthesize state-dependent HTML.
    """
    if not settings.brightdata_live:
        return _mock_fetch(url, state)

    try:
        resp = requests.get(
            url,
            proxies=proxy_for_state(state),
            verify=False,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        return FetchResult(
            url=url,
            state=state,
            html=resp.text,
            status_code=resp.status_code,
            live=True,
            source="residential",
        )
    except Exception as e:
        logger.warning("Bright Data fetch failed for %s @ %s (%s) — falling back to mock", url, state, e)
        return _mock_fetch(url, state)


def serp_search(query: str, state: str = "", num: int = 10) -> list[dict]:
    """
    SERP API search for the Discovery agent (finding new operators).
    Stubbed for the two-geo demo; wired live when BRIGHTDATA_SERP_ZONE is set.
    """
    if not (settings.brightdata_live and settings.BRIGHTDATA_SERP_ZONE):
        return [{"title": f"[mock] result {i+1} for {query}", "url": f"https://example.com/{i+1}"} for i in range(num)]
    # Live SERP via Bright Data: a google search routed through the SERP zone.
    try:
        target = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num}"
        user = proxy_username(state, zone=settings.BRIGHTDATA_SERP_ZONE)
        proxy = f"http://{user}:{settings.BRIGHTDATA_ZONE_PASSWORD}@{settings.BRIGHTDATA_PROXY_HOST}:{settings.BRIGHTDATA_PROXY_PORT}"
        resp = requests.get(target, proxies={"http": proxy, "https": proxy}, verify=False, timeout=60)
        return [{"raw_html": resp.text[:200000], "query": query}]
    except Exception as e:
        logger.warning("SERP search failed (%s) — returning mock", e)
        return [{"title": f"[mock] {query}", "url": "https://example.com"}]


# ── Mock generation (deterministic, state-varying) ────────────────────────────

# Per-state multiplier so the same listing visibly costs different amounts by
# location — this is what makes the geo-price-split demo land with no creds.
_STATE_MULTIPLIER = {
    "CA": 1.00, "NY": 1.08, "TX": 0.84, "FL": 0.92, "WA": 1.04,
    "GA": 0.88, "IL": 0.97, "AZ": 0.86, "NV": 0.90, "CO": 0.95,
}


def _state_factor(state: str) -> float:
    st = (state or "").upper()
    if st in _STATE_MULTIPLIER:
        return _STATE_MULTIPLIER[st]
    # Stable pseudo-random factor in [0.82, 1.10] for any other state.
    h = int(hashlib.sha256(st.encode()).hexdigest(), 16) % 28
    return round(0.82 + h / 100.0, 2)


def _mock_fetch(url: str, state: str) -> FetchResult:
    """
    Build a believable rental-listing checkout page whose totals depend on the
    state. The HTML carries machine-readable data-* attrs the agents can parse,
    so the pipeline runs identically against mock and live pages.
    """
    base_rent = 1995.0
    factor = _state_factor(state)
    advertised = round(base_rent * factor, 2)

    # Drip-priced junk fees, scaled per state.
    fees = [
        ("Mandatory Resort Fee", round(149 * factor, 2), "resort"),
        ("Cleaning Fee", round(95 * factor, 2), "cleaning"),
        ("Application/Admin Fee", round(199 * factor, 2), "admin"),
        ("Mandatory Service Charge", round(89 * factor, 2), "service"),
    ]
    fee_total = round(sum(f[1] for f in fees), 2)
    final = round(advertised + fee_total, 2)

    fee_rows = "\n".join(
        f'        <li class="fee" data-fee-name="{n}" data-fee-type="{t}" data-fee-amount="{a}">{n}: ${a}</li>'
        for n, a, t in fees
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Listing — Atlanta Apartment (MOCK / {state})</title></head>
<body data-mock="true" data-state="{state}">
  <h1 data-listing-title="true">Modern 2BR Apartment — Atlanta, GA</h1>
  <div class="advertised" data-advertised-price="{advertised}">Advertised price: ${advertised}/mo</div>
  <section class="checkout">
    <h2>Checkout summary (state: {state})</h2>
    <ul class="fees">
{fee_rows}
    </ul>
    <div class="total" data-final-price="{final}">Total due today: ${final}</div>
    <p class="note">[MOCK] Generated by FairPrice Watchdog without Bright Data credits. Source URL: {url}</p>
  </section>
</body>
</html>"""
    return FetchResult(url=url, state=state, html=html, status_code=200, live=False, source="mock")
