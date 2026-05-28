"""Quick hunt agent import + wiring test — no DB or Redis needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("FAIRPRICE_DISABLE_CREWAI", "1")

print("=== Scout Agent ===")
from app.agents.scout import ScoutAgent
scout = ScoutAgent()
r = scout.probe("https://example.com/hotel", state="CA", title="Test Hotel")
print("score={} blocked={} prices={} fees={} source={}".format(
    r.score, r.blocked, r.has_prices, r.has_fee_keywords, r.source))
assert r.score > 0, "Expected score > 0"
print("PASS\n")

print("=== Hunt Presets ===")
from app.agents.hunt import HUNT_PRESETS, HuntOrchestrator
for k, v in HUNT_PRESETS.items():
    print("  {}: {} ({})".format(k, v["label"], v["default_city"]))
assert "hotels" in HUNT_PRESETS
assert "rentals" in HUNT_PRESETS
print("PASS\n")

print("=== Discovery Agent (mock SERP) ===")
from app.agents.discovery import DiscoveryAgent
disc = DiscoveryAgent()
results = disc.discover("hotel resort fee Las Vegas", limit=5)
print("Found {} candidates".format(len(results)))
for r in results[:3]:
    url = r.get("url", "?")
    print("  {}".format(url[:70]))
assert len(results) > 0, "Expected candidates"
print("PASS\n")

print("=== Honesty label ===")
from app.agents.types import GeoListing
from app.agents.hunt import HuntOrchestrator
mock_gl = GeoListing(state="CA", advertised_price=1995.0, final_price=2527.0, source="mock", live=False)
live_gl = GeoListing(state="CA", advertised_price=199.0, final_price=249.0, source="residential", live=True)
from app.agents.types import FeeItem
live_gl.fees = [FeeItem(fee_name="Resort Fee", fee_amount=50.0, is_junk_fee=True)]
label_mock = HuntOrchestrator._assign_honesty_label(None, [mock_gl])
label_live = HuntOrchestrator._assign_honesty_label(None, [live_gl])
print("mock listing -> {}".format(label_mock))
print("live listing -> {}".format(label_live))
assert label_mock == "mock_fallback"
assert label_live in ("live_verified", "live_partial")
print("PASS\n")

print("=== Scout blocking detection ===")
from app.agents.scout import ScoutAgent
cloudflare_html = "<title>Just a moment...</title> cloudflare attention required"
assert ScoutAgent._detect_blocking(cloudflare_html)
clean_html = "<div>$199.00 resort fee service fee checkout</div>"
assert not ScoutAgent._detect_blocking(clean_html)
assert ScoutAgent._detect_prices(clean_html)
assert ScoutAgent._detect_fee_keywords(clean_html)
print("PASS\n")

print("=" * 50)
print("ALL HUNT AGENT TESTS PASSED")
print("=" * 50)
