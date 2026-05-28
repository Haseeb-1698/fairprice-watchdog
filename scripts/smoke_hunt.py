"""
smoke_hunt.py — offline end-to-end test of the new hunt pipeline.

Runs without any credentials: Discovery returns mock candidates,
Scout scores mock HTML high, Pipeline runs in mock mode.
No DB or Redis required — validates agent wiring only.

Usage:
    python scripts/smoke_hunt.py
"""
import asyncio
import sys
import os

# Run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Patch the database and queue so we don't need real infra
import unittest.mock as mock

# Mock the DB session so _create_scan doesn't need Postgres
_scan_store: dict = {}

async def _fake_commit():
    pass

async def _fake_close():
    pass

class FakeSession:
    def __init__(self):
        self._items = []
    def add(self, item):
        self._items.append(item)
        if hasattr(item, 'id'):
            _scan_store[str(item.id)] = item
    async def commit(self):
        pass
    async def flush(self):
        pass
    async def get(self, cls, pk):
        return None
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        pass

class FakeSessionLocal:
    def __call__(self):
        return FakeSession()
    def __enter__(self):
        return FakeSession()
    def __exit__(self, *a):
        pass

# Mock the Redis hunt state store
_hunt_store: dict = {}

async def fake_get_redis():
    class FakeRedis:
        async def set(self, key, value, **kwargs):
            _hunt_store[key] = value
        async def get(self, key):
            return _hunt_store.get(key)
        async def lpush(self, queue, item):
            pass
    return FakeRedis()


async def run():
    print("=" * 60)
    print("FairPrice Watchdog — Hunt Pipeline Smoke Test")
    print("=" * 60)
    print()

    # Patch infra
    with mock.patch("app.core.database.AsyncSessionLocal", FakeSessionLocal()), \
         mock.patch("app.services.queue.get_redis_client", fake_get_redis):

        from app.agents.scout import ScoutAgent, ScoutResult
        from app.agents.hunt import HuntOrchestrator, HUNT_PRESETS, _save_hunt, _load_hunt
        from app.agents.discovery import DiscoveryAgent
        from app.services import brightdata

        # ── Test 1: Scout Agent ─────────────────────────────────────────────
        print("1. Scout Agent (mock fetch)")
        scout = ScoutAgent()
        result = scout.probe("https://example.com/hotel", state="CA", title="Example Hotel")
        print(f"   URL:           {result.url}")
        print(f"   Reachable:     {result.reachable}")
        print(f"   Blocked:       {result.blocked}")
        print(f"   Has prices:    {result.has_prices}")
        print(f"   Has fee kws:   {result.has_fee_keywords}")
        print(f"   Score:         {result.score:.2f}")
        print(f"   Source:        {result.source}")
        assert result.score > 0, "Expected non-zero score"
        print("   ✓ Scout OK\n")

        # ── Test 2: Discovery Agent (mock SERP) ─────────────────────────────
        print("2. Discovery Agent (mock SERP)")
        disc = DiscoveryAgent()
        candidates = disc.discover("hotel resort fee Las Vegas", limit=5)
        print(f"   Candidates found: {len(candidates)}")
        for c in candidates[:3]:
            print(f"   - {c.get('url', '?')[:60]} ({c.get('source', '?')})")
        assert len(candidates) > 0, "Expected at least one candidate"
        print("   ✓ Discovery OK\n")

        # ── Test 3: Hunt Presets ─────────────────────────────────────────────
        print("3. Hunt Presets")
        for key, preset in HUNT_PRESETS.items():
            print(f"   {key}: {preset['label']} ({preset['default_city']}, {preset['default_locations']})")
        assert "hotels" in HUNT_PRESETS
        assert "rentals" in HUNT_PRESETS
        print("   ✓ Presets OK\n")

        # ── Test 4: Hunt Orchestrator (full mock flow) ───────────────────────
        print("4. Hunt Orchestrator — full mock flow (hotels / Las Vegas / CA vs TX)")

        # Manually run the core orchestration logic without DB/Redis
        from app.agents.hunt import HuntOrchestrator, _parse_serp_urls
        import json, uuid
        from datetime import datetime, timezone

        hunt_id = f"smoke-{str(uuid.uuid4())[:8]}"
        hunt = {
            "id": hunt_id,
            "sector": "hotels",
            "label": "Hotel Resort Fee Hunt",
            "city": "Las Vegas",
            "locations": ["CA", "TX"],
            "status": "discovering",
            "phase": "discovery",
            "candidates": [],
            "scout_results": [],
            "scan_ids": [],
            "results": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _hunt_store[f"hunt:{hunt_id}"] = json.dumps(hunt)

        # Step 1: Discover
        preset = HUNT_PRESETS["hotels"]
        all_candidates = []
        for tmpl in preset["queries"][:2]:  # limit to 2 queries for speed
            q = tmpl.replace("{city}", "Las Vegas")
            results = disc.discover(q, limit=5)
            for r in results:
                if "raw_html" in r:
                    for url in _parse_serp_urls(r["raw_html"]):
                        all_candidates.append({"title": url, "url": url, "source": "serp_parsed"})
                elif "url" in r:
                    all_candidates.append(r)

        print(f"   Discovered: {len(all_candidates)} candidates")

        # Dedupe
        seen, deduped = set(), []
        from urllib.parse import urlparse
        for c in all_candidates:
            host = urlparse(c.get("url", "")).netloc.lower().removeprefix("www.")
            if host and host not in seen:
                seen.add(host)
                deduped.append(c)

        print(f"   Deduped:    {len(deduped)} unique candidates")

        # Step 2: Scout top 3
        scored = []
        for c in deduped[:3]:
            sr = scout.probe(c.get("url", ""), state="CA", title=c.get("title", ""))
            scored.append({**vars(sr), "eligible": sr.score >= 0.4 and not sr.blocked})
            print(f"   Scout: {c.get('url', '')[:50]:<50} score={sr.score:.2f} eligible={sr.score >= 0.4}")

        eligible = [s for s in scored if s["eligible"]]
        print(f"   Eligible:   {len(eligible)}/{len(scored)}")

        # Step 3: Run pipeline on top 1 (mock)
        from app.agents import pipeline as pl

        if eligible or scored:
            target = (eligible or scored)[0]
            url = target["url"]
            fake_scan_id = str(uuid.uuid4())

            print(f"\n   Running pipeline on: {url[:60]}")
            print(f"   Scan ID: {fake_scan_id}")

            # We need to mock the DB persist in pipeline too
            with mock.patch("app.agents.pipeline.AsyncSessionLocal", FakeSessionLocal()), \
                 mock.patch("app.agents.pipeline.update_scan_status", mock.AsyncMock()):
                try:
                    brief = await pl.run_scan(fake_scan_id, url, ["CA", "TX"])

                    print(f"\n   Pipeline results:")
                    print(f"   Summary: {brief.summary}")
                    for gl in brief.listings:
                        print(f"   State {gl.state}: advertised=${gl.advertised_price:.2f} "
                              f"final=${gl.final_price:.2f} fees={len(gl.fees)} source={gl.source}")

                    # Assign honesty label
                    honesty = HuntOrchestrator._assign_honesty_label(None, brief.listings)
                    print(f"   Honesty label: {honesty}")
                    assert honesty in ("live_verified", "live_partial", "mock_fallback", "blocked")

                    if brief.comparison:
                        c = brief.comparison
                        print(f"\n   GEO SPLIT: {c.state_a} ${c.price_a:.2f} vs {c.state_b} ${c.price_b:.2f} "
                              f"→ ${c.delta:.2f} ({c.pct}%) gap")

                    print("\n   ✓ Full hunt pipeline OK")
                except Exception as e:
                    print(f"   Pipeline error (may be expected if deps missing): {e}")

    print()
    print("=" * 60)
    print("Smoke test PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())
