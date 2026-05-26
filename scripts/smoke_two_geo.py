"""
Smoke test — two-geo demo path in MOCK MODE (no DB, no Redis, no credentials).

Runs Crawler → Journey → Diff for two US states and prints the price split plus
the evidence-vault SHA-256 receipts. Validates the punchline works offline.

    python scripts/smoke_two_geo.py
"""
import os
import sys

# Config requires these; set dummies so this runs with zero real infra.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
# Force offline mock LLM for a deterministic, network-free smoke test.
os.environ["LLM_PROVIDER"] = "mock"

# Windows consoles default to cp1252; make stdout UTF-8 so symbols print.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.crawler import CrawlerAgent          # noqa: E402
from app.agents.diff import DiffAgent                # noqa: E402
from app.agents.journey import JourneyAgent          # noqa: E402
from app.agents.types import FeeItem, GeoComparison, GeoListing  # noqa: E402
from app.services import storage                      # noqa: E402

URL = "https://example.com/atlanta-apartment-123"
STATES = ["CA", "TX"]
SCAN_ID = "smoke-0001"


def scan(state: str) -> GeoListing:
    crawl = CrawlerAgent().load(URL, state)
    walk = JourneyAgent().walk(URL, state)
    diff = DiffAgent().analyze(crawl["advertised_price"], walk["final_price"], walk["fees"])
    snap = storage.store_snapshot(SCAN_ID, state, walk["html"])
    return GeoListing(
        state=state,
        advertised_price=crawl["advertised_price"],
        final_price=walk["final_price"],
        fees=diff["fees"],
        snapshot_sha256=snap.sha256,
        snapshot_path=snap.storage_path,
        source=walk["source"],
        live=walk["live"],
    )


def main() -> int:
    listings = [scan(s) for s in STATES]
    print("\n=== FairPrice Watchdog — two-geo smoke test (MOCK MODE) ===\n")
    for l in listings:
        print(f"  [{l.state}] advertised ${l.advertised_price:>8.2f} → final ${l.final_price:>8.2f} "
              f"| hidden ${l.final_price - l.advertised_price:>7.2f} | junk fees: "
              f"{sum(f.is_junk_fee for f in l.fees)}/{len(l.fees)} | src={l.source}")
        for f in l.fees:
            flag = "JUNK" if f.is_junk_fee else "ok  "
            print(f"        - [{flag}] {f.fee_name:<28} ${f.fee_amount:>7.2f}  {f.ftc_clause or ''}")
        print(f"        evidence sha256: {l.snapshot_sha256[:32]}…  ({l.snapshot_path})")

    cmp = GeoComparison(STATES[0], listings[0].final_price, STATES[1], listings[1].final_price)
    print(f"\n  PUNCHLINE: {cmp.higher_state} is higher by ${cmp.delta:.2f} ({cmp.pct}%) — "
          f"same listing, same moment, two states.\n")

    assert cmp.delta > 0, "expected a price gap between states"
    assert all(l.snapshot_sha256 for l in listings), "every capture must be hashed"
    print("  ✅ PASS — price split detected and evidence hashed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
