"""
live_geo_probe.py — confirm the Bright Data Browser API connects and that
state-level geo targeting (username -country-us-state-xx) actually changes the
exit location. Hits Bright Data's own geo test page (cheap).

    python scripts/live_geo_probe.py
"""
import os
import re
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings        # noqa: E402
from app.services import brightdata          # noqa: E402

TEST_URL = "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api"


def probe(state: str) -> str:
    print(f"\n[{state}] CDP: {brightdata.browser_cdp_url(state)}")
    html = brightdata._fetch_via_browser(TEST_URL, state, timeout=60)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    # Surface the geo-relevant fields the test page reports.
    hits = [kw for kw in ("Country", "State", "Region", "City", "ASN", "IP") if kw.lower() in text.lower()]
    print(f"[{state}] reported fields: {hits}")
    print(f"[{state}] {text[:400]}")
    return text


def main() -> int:
    print(f"brightdata_browser_live = {settings.brightdata_browser_live}")
    if not settings.brightdata_browser_live:
        print("Browser API not configured in .env — aborting.")
        return 1
    for st in ("CA", "TX"):
        try:
            probe(st)
        except Exception as e:
            print(f"[{st}] ERROR: {e}")
    print(f"\nCredits: {__import__('app.services.credits', fromlist=['summary']).summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
