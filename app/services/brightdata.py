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
from app.services import credits

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

# US state codes — anything else is treated as an ISO country code (UK/EU coverage).
_US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY",
}
# Geo codes that are themselves countries (the bare-country path: no -state segment).
_COUNTRY_OVERRIDES = {"US": "us", "GB": "gb", "UK": "gb"}


def proxy_username(state: str, zone: Optional[str] = None) -> str:
    """
    Build a Bright Data proxy username with geo-targeting.

    - If `state` is a US state code (e.g. "CA"), uses country-us + state-<x>.
    - If `state` is "US" / "GB" / an EU ISO code, uses country-<iso> only.

    The geo segment is what makes the same listing resolve to a different price
    by location — the heart of the geo-discrimination proof.
    """
    zone = zone or settings.BRIGHTDATA_RESIDENTIAL_ZONE
    code = (state or "").strip().upper()

    if code in _US_STATES:
        return f"brd-customer-{settings.BRIGHTDATA_CUSTOMER_ID}-zone-{zone}-country-us-state-{code.lower()}"
    if code in _COUNTRY_OVERRIDES:
        return f"brd-customer-{settings.BRIGHTDATA_CUSTOMER_ID}-zone-{zone}-country-{_COUNTRY_OVERRIDES[code]}"
    if code and len(code) == 2:
        # Treat any 2-letter code as an ISO country (EU countries land here).
        return f"brd-customer-{settings.BRIGHTDATA_CUSTOMER_ID}-zone-{zone}-country-{code.lower()}"
    # Fallback — default to US country only.
    return f"brd-customer-{settings.BRIGHTDATA_CUSTOMER_ID}-zone-{zone}-country-us"


def proxy_for_state(state: str) -> dict[str, str]:
    """Return a requests-style proxies dict for the residential zone in `state`."""
    user = proxy_username(state)
    pwd = settings.BRIGHTDATA_RESIDENTIAL_PASSWORD
    host = settings.BRIGHTDATA_PROXY_HOST
    port = settings.BRIGHTDATA_PROXY_PORT
    proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}


def browser_cdp_url(state: str) -> Optional[str]:
    """
    Return the Bright Data Browser API CDP websocket URL for `state`.

    Geo is set by modifying the username (Bright Data: "control your proxy by
    modifying the username"), appending -country-us-state-<st>. This is what
    makes the same listing render at a different price per state — the demo core.
    Journey Simulator (Playwright / Skyvern) connects here. None in mock mode.
    """
    if not settings.brightdata_browser_live:
        return None
    user = proxy_username(state, zone=settings.BRIGHTDATA_BROWSER_ZONE)
    pwd = settings.BRIGHTDATA_BROWSER_PASSWORD
    host = settings.BRIGHTDATA_BROWSER_HOST
    port = settings.BRIGHTDATA_BROWSER_PORT
    return f"wss://{user}:{pwd}@{host}:{port}"


# ── Web Unlocker /request REST API ────────────────────────────────────────────

_REQUEST_API = "https://api.brightdata.com/request"


def _fetch_via_unlocker_api(url: str, zone: str, country: str = "us", timeout: int = 90) -> str:
    """Call Bright Data's /request API (Web Unlocker / SERP). Returns raw HTML."""
    resp = requests.post(
        _REQUEST_API,
        headers={
            "Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"zone": zone, "url": url, "format": "raw", "country": country},
        timeout=(15, timeout),
    )
    resp.raise_for_status()
    return resp.text


def _fetch_via_unlocker_proxy(url: str, state: str, timeout: int = 90) -> str:
    """Fetch through the Web Unlocker in PROXY mode with state geo — anti-bot
    bypass AND state/ZIP targeting in one (needs the unlocker zone password)."""
    user = proxy_username(state, zone=settings.BRIGHTDATA_ZONE)
    pwd = settings.BRIGHTDATA_ZONE_PASSWORD
    proxy = f"http://{user}:{pwd}@{settings.BRIGHTDATA_PROXY_HOST}:{settings.BRIGHTDATA_PROXY_PORT}"
    resp = requests.get(
        url, proxies={"http": proxy, "https": proxy}, verify=False, timeout=(15, timeout),
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    return resp.text


def _fetch_via_browser(url: str, state: str, timeout: int = 90) -> str:
    """Render a page through the Bright Data Browser API (remote CDP) for `state`.

    Needs the `playwright` client package (no local browser install required —
    it connects to Bright Data's remote browser over CDP)."""
    from playwright.sync_api import sync_playwright

    cdp = browser_cdp_url(state)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp, timeout=timeout * 1000)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        html = page.content()
        browser.close()
    return html


# ── Page fetch (Crawler) ──────────────────────────────────────────────────────

def fetch_html(url: str, state: str, timeout: int = 60) -> FetchResult:
    """
    Fetch fully-rendered HTML for `url` as a real user in `state`.

    Live path: route through the Bright Data residential proxy (which fronts the
    Web Unlocker for anti-bot bypass). Mock path: synthesize state-dependent HTML.
    """
    if not settings.brightdata_any_live:
        return _mock_fetch(url, state)

    if not credits.can_spend():
        logger.warning("Bright Data credit cap reached (%d) — using mock to protect budget",
                       settings.BRIGHTDATA_CREDIT_CAP)
        return _mock_fetch(url, state)

    # Priority for a geo-pinned fetch:
    #   1. Residential proxy + state geo    — fast, reliable state targeting (default)
    #   2. Web Unlocker proxy + state geo    — geo + heavy unblock (slower; for blocked sites)
    #   3. Web Unlocker /request API         — strong unlock, country-level only
    #   4. Browser API render                — country-level
    # Residential is first because the Unlocker in proxy mode can stream keepalive
    # bytes that defeat the read timeout on complex sites (observed hangs).
    try:
        if settings.brightdata_live:
            resp = requests.get(url, proxies=proxy_for_state(state), verify=False, timeout=(15, timeout),
                                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            html = resp.text
            source = "residential"
        elif settings.brightdata_unlocker_proxy_live:
            html = _fetch_via_unlocker_proxy(url, state, timeout=timeout)
            source = "unlocker_geo"
        elif settings.brightdata_unlocker_live:
            html = _fetch_via_unlocker_api(url, settings.BRIGHTDATA_ZONE, country="us", timeout=timeout)
            source = "web_unlocker"
        else:  # browser-only credentials
            html = _fetch_via_browser(url, state, timeout=timeout)
            source = "browser_api"
        credits.record()
        return FetchResult(url=url, state=state, html=html, status_code=200, live=True, source=source)
    except Exception as e:
        logger.warning("Bright Data fetch failed for %s @ %s (%s) — falling back to mock", url, state, e)
        return _mock_fetch(url, state)


def serp_search(query: str, state: str = "", num: int = 10) -> list[dict]:
    """
    SERP API search for the Discovery agent (finding new operators).
    Stubbed for the two-geo demo; wired live when BRIGHTDATA_SERP_ZONE is set.
    """
    if not settings.brightdata_serp_live:
        return [{"title": f"[mock] result {i+1} for {query}", "url": f"https://example.com/{i+1}"} for i in range(num)]
    # Live SERP via Bright Data /request API (zone=serp_api1).
    try:
        target = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num}"
        html = _fetch_via_unlocker_api(target, settings.BRIGHTDATA_SERP_ZONE, country="us")
        credits.record()
        return [{"raw_html": html[:200000], "query": query}]
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
