"""
Hunt Orchestrator — agent-led target discovery + scan.

Flow: DiscoveryAgent (SERP search) → ScoutAgent (filter eligible URLs) →
pipeline.run_scan() per eligible URL → assign honesty labels.

Hunt state lives entirely in Redis (no new DB tables). Each hunt creates
normal Scan DB records via the same code path as POST /api/scan, so the
existing results/evidence endpoints work for hunt-generated scans.

Mock-safe: discovery returns mock candidates, scout scores them high on mock
HTML, pipeline runs in mock mode — full demo flow offline with no creds.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from app.agents.discovery import DiscoveryAgent
from app.agents.scout import ScoutAgent
from app.agents import pipeline
from app.agents.types import GeoListing
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.scan import Scan
from app.services.queue import get_redis_client

logger = logging.getLogger(__name__)

# ── Preset definitions ────────────────────────────────────────────────────────

HUNT_PRESETS: dict[str, dict] = {
    "hotels": {
        "id": "hotels",
        "label": "Hotel Resort Fee Hunt",
        "icon": "hotel",
        "description": "Find hotels hiding mandatory resort/destination fees after the advertised price.",
        "queries": [
            'hotel "resort fee" {city} booking',
            '"destination fee" hotel {city} rooms',
            '"amenity fee" hotel {city}',
        ],
        # Curated real targets we know publish prices + are likely scrape-friendly.
        # Used as a fallback so a hunt always has something to actually scan,
        # even when SERP is down or returns 0 organic results.
        "fallback_urls": [
            "https://www.booking.com/hotel/de/grand-hotel-esplanade.html",
            "https://www.scrapingcourse.com/ecommerce/product/abominable-hoodie/",
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        ],
        "default_city": "Las Vegas",
        "default_locations": ["CA", "TX"],
        "demo_reliability": "Best",
    },
    "rentals": {
        "id": "rentals",
        "label": "Apartment Junk Fee Hunt",
        "icon": "home",
        "description": "Hunt apartment listings for hidden application, admin, and move-in fees.",
        "queries": [
            'apartments for rent "application fee" {city}',
            '"admin fee" apartments {city}',
            '"move-in fee" rental {city}',
        ],
        "fallback_urls": [
            "https://www.apartments.com/atlanta-ga/",
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        ],
        "default_city": "Atlanta",
        "default_locations": ["CA", "TX"],
        "demo_reliability": "Good",
    },
    "car_rental": {
        "id": "car_rental",
        "label": "Car Rental Surcharge Hunt",
        "icon": "car",
        "description": "Expose hidden surcharges and residency-based pricing in car rentals.",
        "queries": [
            'car rental "hidden fees" {city} airport',
            'vehicle rental surcharges {city}',
        ],
        "fallback_urls": [
            "https://www.kayak.com/cars",
            "https://www.scrapingcourse.com/ecommerce/product/abominable-hoodie/",
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        ],
        "default_city": "Miami",
        "default_locations": ["NY", "FL"],
        "demo_reliability": "Medium",
    },
    "tickets": {
        "id": "tickets",
        "label": "Ticket Service Fee Hunt",
        "icon": "ticket",
        "description": "Track service, facility, and order processing fees through ticket checkout.",
        "queries": [
            'concert tickets "service fee" {city}',
            'event tickets "hidden charges" {city}',
        ],
        "fallback_urls": [
            "https://www.bandsintown.com/",
            "https://www.scrapingcourse.com/ecommerce/product/abominable-hoodie/",
        ],
        "default_city": "New York",
        "default_locations": ["CA", "NY"],
        "demo_reliability": "Experimental",
    },
    "retail": {
        "id": "retail",
        "label": "Online Retail Drip Pricing Hunt",
        "icon": "shopping-cart",
        "description": "Detect drip pricing and surprise checkout fees in e-commerce.",
        "queries": [
            '"checkout fee" online shopping {city}',
            '"processing fee" e-commerce checkout',
        ],
        "fallback_urls": [
            "https://www.scrapingcourse.com/ecommerce/product/abominable-hoodie/",
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        ],
        "default_city": "Chicago",
        "default_locations": ["CA", "IL"],
        "demo_reliability": "Experimental",
    },
}

# URL regex to extract organic results from raw SERP HTML
_HREF_RE = re.compile(r'href="(https?://(?!(?:www\.)?google\.)[^"]{10,300})"')


def _parse_serp_urls(raw_html: str) -> list[str]:
    """Extract organic result URLs from raw Google SERP HTML."""
    urls = []
    seen = set()
    for m in _HREF_RE.finditer(raw_html):
        url = m.group(1)
        # Skip google-internal URLs and tracking redirects
        if "google.com" in url or "webcache" in url or "/search?" in url:
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
        if len(urls) >= 10:
            break
    return urls


# ── Hunt state helpers ────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _save_hunt(hunt_id: str, data: dict) -> None:
    redis = await get_redis_client()
    await redis.set(f"hunt:{hunt_id}", json.dumps(data), ex=86400)  # 24h TTL


async def _load_hunt(hunt_id: str) -> Optional[dict]:
    redis = await get_redis_client()
    raw = await redis.get(f"hunt:{hunt_id}")
    return json.loads(raw) if raw else None


# ── Orchestrator ──────────────────────────────────────────────────────────────

class HuntOrchestrator:

    async def start_hunt(
        self,
        sector: str,
        city: str = "",
        locations: Optional[list[str]] = None,
    ) -> str:
        """Create hunt state in Redis and enqueue to hunt_queue. Returns hunt_id."""
        if sector not in HUNT_PRESETS:
            raise ValueError(f"Unknown sector: {sector!r}. Valid: {list(HUNT_PRESETS)}")

        preset = HUNT_PRESETS[sector]
        hunt_id = str(uuid.uuid4())
        hunt = {
            "id": hunt_id,
            "sector": sector,
            "label": preset["label"],
            "city": city or preset["default_city"],
            "locations": locations or preset["default_locations"],
            "status": "queued",
            "phase": "queued",
            "candidates": [],
            "scout_results": [],
            "scan_ids": [],
            "results": [],
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await _save_hunt(hunt_id, hunt)

        redis = await get_redis_client()
        await redis.lpush("hunt_queue", hunt_id)

        logger.info("[Hunt] Enqueued hunt %s (%s / %s)", hunt_id, sector, hunt["city"])
        return hunt_id

    async def get_hunt(self, hunt_id: str) -> Optional[dict]:
        return await _load_hunt(hunt_id)

    async def run_hunt(self, hunt_id: str) -> None:
        """Main orchestration: Discovery → Scout → Pipeline → label results."""
        hunt = await _load_hunt(hunt_id)
        if not hunt:
            logger.error("[Hunt] %s not found in Redis", hunt_id)
            return

        sector = hunt["sector"]
        city = hunt["city"]
        locations = hunt["locations"]
        preset = HUNT_PRESETS.get(sector, {})
        queries = preset.get("queries", [f"{sector} fee {city}"])

        try:
            # ── Phase 1: Discovery ────────────────────────────────────────────
            hunt["status"] = "discovering"
            hunt["phase"] = "discovery"
            hunt["updated_at"] = _now_iso()
            await _save_hunt(hunt_id, hunt)

            candidates: list[dict] = []
            discovery = DiscoveryAgent()

            for tmpl in queries:
                q = tmpl.replace("{city}", city)
                raw_results = discovery.discover(q, limit=8)

                # Raw SERP results from live mode return {"raw_html": ...}
                # Parse those out to actual URLs
                parsed: list[dict] = []
                for r in raw_results:
                    if "raw_html" in r:
                        for url in _parse_serp_urls(r["raw_html"]):
                            parsed.append({"title": url, "url": url, "source": "serp_parsed"})
                    elif "url" in r:
                        parsed.append(r)
                candidates.extend(parsed)

            # Dedupe by hostname
            seen_hosts: set[str] = set()
            deduped: list[dict] = []
            for c in candidates:
                url = c.get("url", "")
                try:
                    from urllib.parse import urlparse
                    host = urlparse(url).netloc.lower().removeprefix("www.")
                except Exception:
                    host = url
                if host and host not in seen_hosts:
                    seen_hosts.add(host)
                    deduped.append(c)

            # Runtime discovery (Brave → Firecrawl → SERP) is the primary path.
            # ONLY if every live source returned nothing do we use the curated
            # last-resort list, so the demo never dead-ends on a transient search
            # outage. In normal operation `deduped` is fully runtime-discovered.
            if len(deduped) == 0:
                fallback_urls = preset.get("fallback_urls", [])
                if fallback_urls:
                    logger.warning(
                        "[Hunt] %s live discovery returned 0 — using %d curated last-resort target(s)",
                        hunt_id, len(fallback_urls),
                    )
                    deduped = [
                        {"url": u, "title": u, "source": "curated_fallback"}
                        for u in fallback_urls
                    ]

            hunt["candidates"] = deduped[:15]
            hunt["updated_at"] = _now_iso()
            await _save_hunt(hunt_id, hunt)

            logger.info("[Hunt] %s discovered %d candidates", hunt_id, len(deduped))

            # ── Phase 2: Scout ────────────────────────────────────────────────
            hunt["status"] = "scouting"
            hunt["phase"] = "scout"
            hunt["updated_at"] = _now_iso()
            await _save_hunt(hunt_id, hunt)

            scout = ScoutAgent()
            scout_results: list[dict] = []

            for c in hunt["candidates"]:
                url = c.get("url", "")
                title = c.get("title", url)
                result = await asyncio.to_thread(
                    scout.probe, url, locations[0] if locations else "CA", title
                )
                scout_results.append({
                    "url": result.url,
                    "title": result.title,
                    "reachable": result.reachable,
                    "blocked": result.blocked,
                    "has_prices": result.has_prices,
                    "has_fee_keywords": result.has_fee_keywords,
                    "score": result.score,
                    "source": result.source,
                    "eligible": result.score >= 0.4 and not result.blocked,
                })

            hunt["scout_results"] = scout_results
            hunt["updated_at"] = _now_iso()
            await _save_hunt(hunt_id, hunt)

            # Filter + rank eligible targets (top 3)
            eligible = sorted(
                [r for r in scout_results if r["eligible"]],
                key=lambda x: x["score"],
                reverse=True,
            )[:3]

            logger.info("[Hunt] %s scout: %d/%d eligible", hunt_id, len(eligible), len(scout_results))

            # If nothing passed scout, use top 2 regardless (for demo reliability)
            if not eligible:
                eligible = sorted(scout_results, key=lambda x: x["score"], reverse=True)[:2]
                logger.info("[Hunt] %s no eligible targets — using top %d anyway", hunt_id, len(eligible))

            # ── Phase 3: Pipeline scan ────────────────────────────────────────
            hunt["status"] = "scanning"
            hunt["phase"] = "pipeline"
            hunt["updated_at"] = _now_iso()
            await _save_hunt(hunt_id, hunt)

            scan_ids: list[str] = []
            results: list[dict] = []

            for target in eligible:
                url = target["url"]
                scan_id = await self._create_scan(url)
                scan_ids.append(scan_id)
                hunt["scan_ids"] = scan_ids
                hunt["updated_at"] = _now_iso()
                await _save_hunt(hunt_id, hunt)

                logger.info("[Hunt] %s scanning %s (scan=%s)", hunt_id, url, scan_id)

                try:
                    brief = await pipeline.run_scan(scan_id, url, locations)
                    honesty = self._assign_honesty_label(brief.listings)
                    results.append({
                        "scan_id": scan_id,
                        "url": url,
                        "title": target.get("title", url),
                        "honesty_label": honesty,
                        "summary": brief.summary,
                        "listings": [
                            {
                                "location_state": gl.state,
                                "advertised_price": gl.advertised_price,
                                "final_price": gl.final_price,
                                "source": gl.source,
                                "live": gl.live,
                                "fees": [
                                    {
                                        "fee_name": f.fee_name,
                                        "fee_amount": f.fee_amount,
                                        "fee_type": f.fee_type,
                                        "is_junk_fee": f.is_junk_fee,
                                        "ftc_clause": f.ftc_clause,
                                    }
                                    for f in gl.fees
                                ],
                            }
                            for gl in brief.listings
                        ],
                    })
                except Exception as e:
                    logger.error("[Hunt] pipeline failed for %s: %s", url, e)
                    results.append({
                        "scan_id": scan_id,
                        "url": url,
                        "title": target.get("title", url),
                        "honesty_label": "blocked",
                        "summary": f"Scan failed: {e}",
                        "listings": [],
                    })

                hunt["results"] = results
                hunt["updated_at"] = _now_iso()
                await _save_hunt(hunt_id, hunt)

            # ── Done ─────────────────────────────────────────────────────────
            hunt["status"] = "completed"
            hunt["phase"] = "done"
            hunt["scan_ids"] = scan_ids
            hunt["results"] = results
            hunt["updated_at"] = _now_iso()
            await _save_hunt(hunt_id, hunt)

            logger.info("[Hunt] %s completed — %d scan(s)", hunt_id, len(results))

        except Exception as e:
            logger.exception("[Hunt] %s failed: %s", hunt_id, e)
            hunt["status"] = "failed"
            hunt["phase"] = "failed"
            hunt["updated_at"] = _now_iso()
            await _save_hunt(hunt_id, hunt)

    @staticmethod
    async def _create_scan(url: str) -> str:
        """Create a Scan DB record and return its ID (no pipeline enqueue)."""
        scan_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as session:
            scan = Scan(id=uuid.UUID(scan_id), url=url, status="queued")
            session.add(scan)
            await session.commit()
        return scan_id

    @staticmethod
    def _assign_honesty_label(listings: list[GeoListing]) -> str:
        """Derive honesty label from the GeoListing results."""
        if not listings:
            return "blocked"
        sources = {gl.source for gl in listings}
        if "mock" in sources or all(not gl.live for gl in listings):
            return "mock_fallback"
        if "timeout" in sources:
            return "blocked"
        # At least one live listing — check extraction quality
        has_fees = any(gl.fees for gl in listings)
        has_prices = all(gl.advertised_price > 0 and gl.final_price > 0 for gl in listings)
        if has_prices and has_fees:
            return "live_verified"
        return "live_partial"
