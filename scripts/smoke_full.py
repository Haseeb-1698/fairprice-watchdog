"""
smoke_full.py — offline end-to-end exercise of the full agent set (no infra).

Crawler → Journey → Diff → Law-Mapper → (two-geo compare) → Discovery → Filing.
Runs in MOCK mode with zero credentials and validates that fees get FTC clauses,
the geo split is detected, discovery returns candidates, and a structured
complaint with hashed exhibits is produced.

    python scripts/smoke_full.py
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ["LLM_PROVIDER"] = "mock"
# Force offline: blank Bright Data creds so the smoke test never spends credits.
for _k in ("BRIGHTDATA_API_KEY", "BRIGHTDATA_ZONE", "BRIGHTDATA_ZONE_PASSWORD",
           "BRIGHTDATA_BROWSER_ZONE", "BRIGHTDATA_BROWSER_PASSWORD", "BRIGHTDATA_SERP_ZONE"):
    os.environ[_k] = ""
os.environ["STORAGE_BACKEND"] = "local"   # no network; write to ./evidence_store
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.crawler import CrawlerAgent           # noqa: E402
from app.agents.diff import DiffAgent                 # noqa: E402
from app.agents.discovery import DiscoveryAgent       # noqa: E402
from app.agents.filing import FilingAgent             # noqa: E402
from app.agents.journey import JourneyAgent           # noqa: E402
from app.agents.law_mapper import LawMapperAgent      # noqa: E402
from app.agents.types import GeoComparison, GeoListing, ScanBrief  # noqa: E402
from app.services import storage                       # noqa: E402

URL = "https://example.com/atlanta-apartment-123"
STATES = ["CA", "TX"]
SCAN_ID = "smoke-full-0001"


def scan(state: str) -> GeoListing:
    crawl = CrawlerAgent().load(URL, state)
    walk = JourneyAgent().walk(URL, state)
    diff = DiffAgent().analyze(crawl["advertised_price"], walk["final_price"], walk["fees"])
    fees = LawMapperAgent().enrich(diff["fees"])
    snap = storage.store_snapshot(SCAN_ID, state, walk["html"])
    return GeoListing(
        state=state, advertised_price=crawl["advertised_price"], final_price=walk["final_price"],
        fees=fees, snapshot_sha256=snap.sha256, snapshot_path=snap.storage_path, source=walk["source"],
    )


def main() -> int:
    listings = [scan(s) for s in STATES]
    cmp = GeoComparison(STATES[0], listings[0].final_price, STATES[1], listings[1].final_price)
    brief = ScanBrief(scan_id=SCAN_ID, url=URL, listings=listings, comparison=cmp)
    brief.summary = (f"{cmp.higher_state} higher by ${cmp.delta:.2f} ({cmp.pct}%)")

    print("\n=== FULL PIPELINE SMOKE (MOCK MODE) ===\n")
    for l in listings:
        print(f"  [{l.state}] ${l.advertised_price:.2f} -> ${l.final_price:.2f}  "
              f"({sum(f.is_junk_fee for f in l.fees)} junk fees)")
        for f in l.fees:
            print(f"      - {f.fee_name:<26} ${f.fee_amount:>7.2f}  [{'JUNK' if f.is_junk_fee else 'ok'}]  {f.ftc_clause}")

    print(f"\n  GEO: {brief.summary}")

    candidates = DiscoveryAgent().discover("apartments atlanta application fee", limit=5)
    print(f"\n  DISCOVERY: {len(candidates)} candidate operator(s) found")

    complaint = FilingAgent().build_complaint(brief, "ftc")
    print(f"\n  FILING: '{complaint['title']}'")
    print(f"     counts={len(complaint['counts'])}  total junk=${complaint['total_junk_fees_usd']:.2f}  "
          f"exhibits={len(complaint['evidence_exhibits'])}")
    if complaint["geo_discrimination"]:
        print(f"     geo finding: {complaint['geo_discrimination']['statement']}")
    print(f"     bundle stored: {complaint.get('_bundle_path')}")

    # Assertions
    assert all(f.ftc_clause for l in listings for f in l.fees), "every fee must get an FTC clause"
    assert cmp.discrimination_detected, "geo gap must be detected"
    assert complaint["evidence_exhibits"], "complaint must include hashed exhibits"
    assert complaint["geo_discrimination"], "complaint must include the geo finding"
    print("\n  ✅ PASS — clauses mapped, geo split found, complaint + exhibits generated.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
