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


# Heuristic: detect responses that LOOK successful but are actually empty,
# a captcha challenge page, or an access-denied stub. Those should NOT count
# as a live success — we want to cascade to the next strategy instead.
_BAD_HTML_TOKENS = (
    "access denied", "are you a robot", "verify you are human",
    "checking your browser", "cloudflare", "unusual traffic",
    "captcha", "blocked", "request blocked",
)


def _is_real_html(html: str) -> bool:
    """True if the response looks like real page content (not a stub/challenge)."""
    if not html:
        return False
    if len(html) < 1500:
        return False
    lo = html.lower()
    if "<html" not in lo and "<!doctype" not in lo:
        return False
    if any(tok in lo[:6000] for tok in _BAD_HTML_TOKENS):
        return False
    return True


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


# ── Screenshot capture (visual evidence) ──────────────────────────────────────

def fetch_screenshot(url: str, geo: str = "", timeout: int = 70) -> Optional[bytes]:
    """
    Capture a full-page PNG screenshot of `url` via the Web Unlocker /request API
    (data_format=screenshot). Returns PNG bytes, or None if unavailable.

    This is the visual evidence companion to the HTML capture — a court exhibit
    showing the actual rendered checkout, sealed with its own SHA-256 hash.
    """
    if not settings.brightdata_unlocker_live:
        return None
    if not credits.can_spend():
        return None
    country = _country_for(geo) if geo else "us"
    try:
        resp = requests.post(
            _REQUEST_API,
            headers={
                "Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "zone": settings.BRIGHTDATA_ZONE,
                "url": url,
                "format": "raw",
                "data_format": "screenshot",
                "country": country,
            },
            timeout=(15, timeout),
        )
        resp.raise_for_status()
        content = resp.content
        # Validate it's actually a PNG/JPEG (Bright Data sends image bytes with a
        # JSON content-type header). Reject error payloads.
        if content[:8].startswith(b"\x89PNG") or content[:3] == b"\xff\xd8\xff":
            credits.record()
            logger.info("[BD] screenshot %s @ %s → %d bytes", url, geo, len(content))
            return content
        logger.warning("[BD] screenshot for %s returned non-image (%d bytes)", url, len(content))
        return None
    except Exception as e:
        logger.warning("[BD] screenshot failed for %s @ %s: %s", url, geo, e)
        return None


# ── Page fetch (Crawler) ──────────────────────────────────────────────────────

def _residential_get(url: str, state: str, timeout: int) -> str:
    """Direct residential-proxy GET. Used for state-level geo on friendly sites.

    Aggressive timeouts (8s connect, 22s read) and disabled retries so
    Cloudflare-walled sites fail fast and we cascade to Unlocker quickly.
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(total=0, connect=0, read=0))
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    resp = session.get(
        url, proxies=proxy_for_state(state), verify=False,
        timeout=(8, min(22, timeout)),
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        allow_redirects=True, stream=False,
    )
    return resp.text


def _unlocker_request(url: str, country: str, timeout: int, render_js: bool = False) -> str:
    """Web Unlocker /request API — handles Cloudflare/CAPTCHA automatically.
    Country-level geo only. `render_js=True` runs the page through a real browser
    on Bright Data's side (slower but works for JS-heavy sites)."""
    if not settings.BRIGHTDATA_API_KEY or not settings.BRIGHTDATA_ZONE:
        raise RuntimeError("Web Unlocker not configured")
    body = {"zone": settings.BRIGHTDATA_ZONE, "url": url, "format": "raw", "country": country}
    if render_js:
        body["data_format"] = "html"   # request a fully-rendered HTML page
        body["render"] = True
    resp = requests.post(
        _REQUEST_API,
        headers={
            "Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=(15, timeout),
    )
    resp.raise_for_status()
    return resp.text


def _run_with_hard_deadline(fn, deadline_s: float, *args, **kwargs):
    """Run `fn` in a daemon thread with a hard wall-clock deadline.

    If the call exceeds the deadline, raise TimeoutError immediately — the
    underlying worker thread is left as a daemon (Python can't kill threads
    cleanly), so it cannot block the pipeline. Crucial: we deliberately do
    NOT use `with ThreadPoolExecutor(...) as pool` because that calls
    pool.shutdown(wait=True) on exit and would block waiting for the hung
    thread to return.
    """
    import threading
    result: list = []
    error: list = []

    def _target():
        try:
            result.append(fn(*args, **kwargs))
        except BaseException as e:  # noqa: BLE001
            error.append(e)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=deadline_s)
    if t.is_alive():
        # Thread still running past the deadline — give up on it, move on.
        raise TimeoutError(f"fetch exceeded hard deadline of {deadline_s}s")
    if error:
        raise error[0]
    return result[0] if result else ""


# Map ISO country codes the Web Unlocker accepts — covers our advertised regions.
_UNLOCKER_COUNTRY_FOR_GEO = {
    "US": "us", "GB": "gb", "UK": "gb",
    "DE": "de", "FR": "fr", "IT": "it", "ES": "es", "NL": "nl", "BE": "be",
    "PL": "pl", "SE": "se", "FI": "fi", "DK": "dk", "IE": "ie", "PT": "pt",
    "AT": "at", "CZ": "cz", "GR": "gr", "HU": "hu", "RO": "ro", "BG": "bg",
    "HR": "hr", "SK": "sk", "SI": "si", "LT": "lt", "LV": "lv", "EE": "ee",
    "CY": "cy", "MT": "mt", "LU": "lu",
}


def _country_for(geo: str) -> str:
    """Best-effort ISO country code for a geo code. US states → 'us'."""
    g = (geo or "").upper()
    if g in _US_STATES:
        return "us"
    return _UNLOCKER_COUNTRY_FOR_GEO.get(g, "us")


def fetch_html(url: str, state: str, timeout: int = 60, scan_id: str | None = None) -> FetchResult:
    """
    Fetch HTML for `url` as a real user in `state`/`country`.

    Multi-strategy chain — each step has a HARD wall-clock deadline so a hung
    `requests` call (HTTPS-over-proxy CONNECT issue) can't lock the pipeline:

        1. Residential proxy (geo precise; fast) ─── 35s deadline
        2. Web Unlocker /request (anti-bot bypass; country-level) ─── 45s deadline
        3. Web Unlocker /request + render_js (JS-heavy sites) ──────── 60s deadline
        4. Mock fallback

    For US-state pairs (CA/TX/etc), step 1 is the only one with true state geo;
    on Cloudflare-walled sites it'll timeout fast and we fall to step 2 which
    handles the unblocking but at country level.
    """
    if not settings.brightdata_any_live:
        return _mock_fetch(url, state)
    if not credits.can_spend():
        logger.warning("Bright Data credit cap reached (%d) — using mock", settings.BRIGHTDATA_CREDIT_CAP)
        return _mock_fetch(url, state)

    country = _country_for(state)
    state_upper = (state or "").upper()
    is_us_state = state_upper in _US_STATES

    # Lazy import to avoid a hard dep cycle if events module is missing.
    def _ev(level: str, message: str, **data):
        if not scan_id:
            return
        try:
            from app.services.events import sync_emit
            sync_emit(scan_id, "Bright Data", level, message, state=state, **data)
        except Exception:
            pass

    # Strategy 1: Web Unlocker /request — proven reliable (anti-bot bypass, country-level).
    # Called directly (no thread wrapper) because `requests` to api.brightdata.com is
    # a clean HTTPS POST with its own connect+read timeout that fires reliably.
    if settings.brightdata_unlocker_live:
        _ev("thinking", f"Web Unlocker /request · country={country} · 45s timeout")
        logger.warning("[BD] unlocker /request try: %s country=%s", url, country)
        try:
            html = _unlocker_request(url, country, timeout=45)
            if _is_real_html(html):
                credits.record()
                _ev("result", f"Web Unlocker succeeded · {len(html)} bytes", bytes=len(html), strategy="web_unlocker")
                return FetchResult(url=url, state=state, html=html, status_code=200,
                                   live=True, source="web_unlocker")
            else:
                logger.warning("[BD] unlocker returned non-page content (%d bytes) — cascading", len(html))
                _ev("warn", f"Unlocker returned stub ({len(html)} bytes) -> cascading", strategy="web_unlocker")
        except Exception as e:
            logger.warning("[BD] unlocker /request failed (%s) — trying with render_js", e)
            _ev("warn", f"Unlocker plain failed: {str(e)[:120]} -> trying with JS render", strategy="web_unlocker")

    # Strategy 2: Residential proxy with state geo (US-state pairs only).
    # Reserved for cases where state-level geo matters more than anti-bot bypass.
    # Note: residential through proxy CONNECT can hang on Cloudflare-walled sites
    # past the deadline (Python threading limitation with C-level socket blocks).
    if is_us_state and settings.brightdata_live:
        _ev("thinking", f"Residential proxy + state geo · {state} · 30s deadline (fallback)")
        logger.warning("[BD] residential-state try: %s @ %s", url, state)
        try:
            html = _run_with_hard_deadline(_residential_get, 30.0, url, state, 22)
            if _is_real_html(html):
                credits.record()
                _ev("result", f"Residential succeeded · {len(html)} bytes", bytes=len(html), strategy="residential")
                return FetchResult(url=url, state=state, html=html, status_code=200,
                                   live=True, source="residential")
            else:
                logger.warning("[BD] residential returned stub (%d bytes) — cascading", len(html))
                _ev("warn", f"Residential returned stub ({len(html)} bytes) -> cascading", strategy="residential")
        except Exception as e:
            logger.warning("[BD] residential failed (%s)", e)
            _ev("warn", f"Residential timed out/failed: {str(e)[:120]}", strategy="residential")

    # Strategy 3: Web Unlocker /request with JS rendering for stubborn sites.
    if settings.brightdata_unlocker_live:
        _ev("thinking", f"Web Unlocker + render_js · country={country} · 60s timeout")
        try:
            html = _unlocker_request(url, country, timeout=60, render_js=True)
            if _is_real_html(html):
                credits.record()
                _ev("result", f"Unlocker+JS succeeded · {len(html)} bytes", bytes=len(html), strategy="web_unlocker_js")
                return FetchResult(url=url, state=state, html=html, status_code=200,
                                   live=True, source="web_unlocker_js")
            else:
                logger.warning("[BD] unlocker+JS stub (%d bytes)", len(html))
                _ev("warn", f"Unlocker+JS stub ({len(html)} bytes)", strategy="web_unlocker_js")
        except Exception as e:
            logger.warning("[BD] unlocker + render_js failed (%s)", e)
            _ev("warn", f"Unlocker+JS failed: {str(e)[:120]}", strategy="web_unlocker_js")

    # Strategy 4: Browser API (last resort).
    if settings.brightdata_browser_live:
        _ev("thinking", f"Browser API (Playwright over CDP) · 75s deadline")
        try:
            html = _run_with_hard_deadline(_fetch_via_browser, 75.0, url, state, 70)
            credits.record()
            _ev("result", f"Browser API succeeded · {len(html)} bytes", bytes=len(html), strategy="browser_api")
            return FetchResult(url=url, state=state, html=html, status_code=200,
                               live=True, source="browser_api")
        except Exception as e:
            logger.warning("[BD] browser API failed (%s)", e)
            _ev("warn", f"Browser API failed: {str(e)[:120]}", strategy="browser_api")

    logger.warning("[BD] all strategies failed for %s @ %s — mock", url, state)
    _ev("error", "All live strategies exhausted → falling to representative mock data", strategy="mock")
    return _mock_fetch(url, state)


def _serp_request(query: str, num: int) -> str:
    """Call Bright Data SERP API directly. Returns raw Google SERP HTML."""
    target = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num}"
    if not settings.BRIGHTDATA_API_KEY or not settings.BRIGHTDATA_SERP_ZONE:
        raise RuntimeError("SERP zone not configured")
    resp = requests.post(
        _REQUEST_API,
        headers={
            "Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"zone": settings.BRIGHTDATA_SERP_ZONE, "url": target, "format": "raw"},
        timeout=(15, 40),
    )
    resp.raise_for_status()
    return resp.text


def serp_search(query: str, state: str = "", num: int = 10) -> list[dict]:
    """
    SERP API search for the Discovery agent (finding new operators).
    Calls Bright Data /request directly (no thread wrapper — that path caused
    the deadlock we fixed for the regular Unlocker). Returns the raw HTML so
    Hunt's _parse_serp_urls can extract organic result links.
    """
    if not settings.brightdata_serp_live:
        return []
    try:
        html = _serp_request(query, num)
        credits.record()
        if _is_real_html(html):
            return [{"raw_html": html[:200000], "query": query}]
        logger.warning("SERP returned stub (%d bytes) for '%s'", len(html), query)
        return []
    except Exception as e:
        logger.warning("SERP search failed for '%s' (%s)", query, e)
        return []


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
