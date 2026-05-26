"""
live_check.py — validate the geo-price split against a REAL site (no DB needed).

Fetches the same URL from two US states through Bright Data and reports whether
the response was live or mock, the advertised/final prices each side extracted,
the geo delta, and the credit spend so far.

    python scripts/live_check.py "https://www.apartments.com/some-listing/" CA TX

Goes live only when Bright Data creds are in .env; otherwise it exercises the
exact same path in mock mode so you can dry-run before spending credits.
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import extract                       # noqa: E402
from app.core.config import settings                 # noqa: E402
from app.services import brightdata, credits          # noqa: E402

DEFAULT_URL = "https://www.apartments.com/"


def check(url: str, state: str) -> dict:
    r = brightdata.fetch_html(url, state)
    advertised = extract.parse_advertised_price(r.html)
    final = extract.parse_final_price(r.html)
    fees = extract.parse_fee_items(r.html)
    return {
        "state": state, "live": r.live, "source": r.source, "status": r.status_code,
        "bytes": r.bytes, "advertised": advertised, "final": final, "fees": len(fees),
    }


def main() -> int:
    args = sys.argv[1:]
    url = args[0] if args else DEFAULT_URL
    states = args[1:3] if len(args) >= 3 else settings.default_states

    print(f"\n=== Live geo check ===\nURL:    {url}\nStates: {states}")
    print(f"Bright Data live: {settings.brightdata_live}  "
          f"(Browser API live: {settings.brightdata_browser_live})\n")

    results = [check(url, st) for st in states]
    for r in results:
        mode = "LIVE" if r["live"] else "MOCK"
        print(f"  [{r['state']}] {mode:4} via {r['source']:12} http={r['status']} "
              f"{r['bytes']:>8}B | advertised={r['advertised']} final={r['final']} fees={r['fees']}")

    a, b = results[0], results[1]
    base = a["final"] or a["advertised"]
    other = b["final"] or b["advertised"]
    if base and other:
        delta = round(abs(base - other), 2)
        pct = round(delta / min(base, other) * 100, 1)
        verdict = "GEO PRICE GAP DETECTED" if delta >= 1 else "no meaningful difference"
        print(f"\n  {a['state']} {base} vs {b['state']} {other} -> ${delta} ({pct}%): {verdict}")
    else:
        print("\n  Could not extract comparable prices — _walk_live / selectors may need site tuning.")

    print(f"\n  Credits: {credits.summary()}\n")
    if not settings.brightdata_live:
        print("  NOTE: mock mode. Fill BRIGHTDATA_* in .env to run live.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
