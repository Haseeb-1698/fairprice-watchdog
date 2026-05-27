"""
pipeline.py — two-geo scan orchestration (Day-3 demo centerpiece).

Entrypoint: `run_scan(scan_id, url, states)` (async, called by the worker).

Flow per state (run in parallel — the Fathom fan-out pattern, async edition):
    Crawler.load → Journey.walk → Diff.analyze → store HTML snapshot in vault
Then: build the GeoComparison (two-state price split) and persist everything to
Postgres (Listing / Fee / EvidenceSnapshot) and the evidence vault.

Orchestration: prefers the CrewAI crew (PRD primary orchestrator) when available;
falls back to calling the agents directly so the demo never depends on the LLM
correctly driving a multi-agent conversation.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from app.agents.crawler import CrawlerAgent
from app.agents.diff import DiffAgent
from app.agents.journey import JourneyAgent
from app.agents.law_mapper import LawMapperAgent
from app.agents.types import GeoComparison, GeoListing, ScanBrief
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.evidence_snapshot import EvidenceSnapshot
from app.models.fee import Fee
from app.models.listing import Listing
from app.models.scan import Scan
from app.services import storage
from app.services.queue import update_scan_status

logger = logging.getLogger(__name__)

# Hard wall-clock cap per state (crawl + checkout walk + diff + snapshot).
PER_STATE_TIMEOUT = int(os.environ.get("SCAN_PER_STATE_TIMEOUT", "180"))


# ── Per-state work (blocking; run in a thread) ────────────────────────────────

def scan_state(scan_id: str, url: str, state: str) -> GeoListing:
    """Crawl + walk + diff + snapshot a listing for one US state."""
    crawl = CrawlerAgent().load(url, state)
    journey = JourneyAgent().walk(url, state)
    diff = DiffAgent().analyze(crawl["advertised_price"], journey["final_price"], journey["fees"])
    # Law-Mapper sets the authoritative FTC clause (and can upgrade junk status).
    fees = LawMapperAgent().enrich(diff["fees"])

    snap = storage.store_snapshot(scan_id, state, journey["html"])

    return GeoListing(
        state=state,
        advertised_price=round(crawl["advertised_price"], 2),
        final_price=round(journey["final_price"], 2),
        fees=fees,
        html=journey["html"],
        snapshot_sha256=snap.sha256,
        snapshot_path=snap.storage_path,
        snapshot_url=snap.public_url,
        source=journey["source"],
        live=journey["live"],
    )


# ── Public entrypoint ─────────────────────────────────────────────────────────

async def run_scan(scan_id: str, url: str, states: list[str] | None = None) -> ScanBrief:
    """Run a full two-geo scan and persist results. Returns the ScanBrief."""
    states = states or settings.default_states
    logger.info("▶ Scan %s starting: %s across %s", scan_id, url, states)
    await update_scan_status(scan_id, "processing")

    try:
        listings = await _execute(scan_id, url, states)

        comparison = None
        if len(listings) >= 2:
            comparison = GeoComparison(
                state_a=listings[0].state, price_a=listings[0].final_price,
                state_b=listings[1].state, price_b=listings[1].final_price,
            )

        brief = ScanBrief(scan_id=scan_id, url=url, listings=listings, comparison=comparison)
        brief.summary = _summarize(brief)

        await _persist(brief)
        await update_scan_status(scan_id, "completed")
        logger.info("✔ Scan %s complete — %s", scan_id, brief.summary)
        return brief
    except Exception as e:
        logger.exception("✘ Scan %s failed: %s", scan_id, e)
        await update_scan_status(scan_id, "failed")
        await _mark_scan(scan_id, "failed")
        raise


async def _execute(scan_id: str, url: str, states: list[str]) -> list[GeoListing]:
    """Use CrewAI when available; otherwise run agents directly (parallel)."""
    if not os.environ.get("FAIRPRICE_DISABLE_CREWAI"):
        try:
            from app.agents.crew import run_crew_scan
            listings = await asyncio.to_thread(run_crew_scan, scan_id, url, states)
            if listings:
                return listings
        except Exception as e:
            logger.warning("CrewAI orchestration unavailable (%s) — direct agent path", e)

    # Deterministic parallel fan-out (one thread per state), each hard-capped so
    # a slow/blocked fetch can never hang the worker.
    async def _one(st: str) -> GeoListing:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(scan_state, scan_id, url, st), timeout=PER_STATE_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error("State %s timed out after %ss — recording empty listing", st, PER_STATE_TIMEOUT)
            return GeoListing(state=st, advertised_price=0.0, final_price=0.0, source="timeout")

    return list(await asyncio.gather(*[_one(st) for st in states]))


def _summarize(brief: ScanBrief) -> str:
    if brief.comparison and brief.comparison.discrimination_detected:
        c = brief.comparison
        return (
            f"Same listing, same moment: {c.higher_state} ${max(c.price_a, c.price_b):.2f} vs "
            f"{c.state_a if c.higher_state == c.state_b else c.state_b} "
            f"${min(c.price_a, c.price_b):.2f} — a ${c.delta:.2f} ({c.pct}%) geo gap."
        )
    junk = sum(1 for l in brief.listings for f in l.fees if f.is_junk_fee)
    return f"{len(brief.listings)} location(s) scanned; {junk} junk fee(s) flagged."


# ── Persistence ───────────────────────────────────────────────────────────────

async def _persist(brief: ScanBrief) -> None:
    async with AsyncSessionLocal() as session:
        scan = await session.get(Scan, uuid.UUID(brief.scan_id))
        if scan:
            scan.status = "completed"

        for gl in brief.listings:
            listing = Listing(
                scan_id=uuid.UUID(brief.scan_id),
                advertised_price=gl.advertised_price,
                final_price=gl.final_price,
                location_state=gl.state,
            )
            session.add(listing)
            await session.flush()  # populate listing.id for FK

            for fee in gl.fees:
                session.add(Fee(
                    listing_id=listing.id,
                    fee_name=fee.fee_name,
                    fee_amount=fee.fee_amount,
                    fee_type=fee.fee_type,
                    is_junk_fee=fee.is_junk_fee,
                    ftc_clause=fee.ftc_clause,
                ))

            session.add(EvidenceSnapshot(
                scan_id=uuid.UUID(brief.scan_id),
                html_content=gl.html,
                sha256_hash=gl.snapshot_sha256 or "",
                timestamp=datetime.now(timezone.utc),
                storage_path=gl.snapshot_path,
            ))

        await session.commit()


async def _mark_scan(scan_id: str, status: str) -> None:
    try:
        async with AsyncSessionLocal() as session:
            scan = await session.get(Scan, uuid.UUID(scan_id))
            if scan:
                scan.status = status
                await session.commit()
    except Exception:
        logger.debug("could not mark scan %s as %s", scan_id, status)
