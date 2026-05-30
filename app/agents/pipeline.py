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
from app.agents import vision
from app.agents.types import GeoComparison, GeoListing, ScanBrief
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.evidence_snapshot import EvidenceSnapshot
from app.models.fee import Fee
from app.models.listing import Listing
from app.models.scan import Scan
from app.services import storage, brightdata, memory
from app.services.events import sync_emit, clear as clear_events
from app.services.queue import update_scan_status

logger = logging.getLogger(__name__)

# Hard wall-clock cap per state (crawl + checkout walk + diff + snapshot).
# 300s = 5 minutes per state — generous enough to cover the multi-strategy
# fetch chain (residential 35s + unlocker 45s + unlocker+JS 60s) plus 3 LLM
# extraction passes (~30s each) plus storage. Override via env if needed.
PER_STATE_TIMEOUT = int(os.environ.get("SCAN_PER_STATE_TIMEOUT", "300"))


# ── Per-state work (blocking; run in a thread) ────────────────────────────────

def scan_state(scan_id: str, url: str, state: str) -> GeoListing:
    """Crawl + walk + diff + snapshot a listing for one US state.
    Emits per-step events so the UI can render an agent thinking feed."""
    sync_emit(scan_id, "Crawler", "started", f"Loading listing from {state}", state=state, url=url)
    crawl = CrawlerAgent().load(url, state, scan_id=scan_id)
    sync_emit(
        scan_id, "Crawler", "result",
        f"Advertised price from {state}: ${crawl['advertised_price']:.2f}",
        state=state, advertised_price=crawl["advertised_price"],
        source=crawl.get("source"), live=crawl.get("live"),
    )

    sync_emit(scan_id, "Journey Simulator", "started",
              f"Walking the checkout funnel from {state} (stops before payment)", state=state)
    journey = JourneyAgent().walk(url, state, scan_id=scan_id)
    sync_emit(
        scan_id, "Journey Simulator", "result",
        f"Final total from {state}: ${journey['final_price']:.2f} · {len(journey['fees'])} fee line-item(s)",
        state=state, final_price=journey["final_price"],
        fee_count=len(journey["fees"]),
        source=journey.get("source"), live=journey.get("live"),
    )

    # Capture the rendered screenshot (JS has executed in Bright Data's browser)
    # so we can (a) seal it as evidence and (b) read prices off it with vision
    # when the raw HTML had none. Heavy pages sometimes get captured before they
    # finish rendering, so we retry up to MAX_SHOT_TRIES — a fresh capture is a
    # fresh render and is likely to catch the loaded page. We keep the LARGEST
    # screenshot (more rendered = bigger) and stop early once vision finds a price.
    MAX_SHOT_TRIES = 2
    shot_png = shot_sha = shot_path = None
    if journey.get("live"):
        _weak = lambda: (crawl["advertised_price"] < 5 or journey["final_price"] < 5)
        best_png = None
        for attempt in range(1, MAX_SHOT_TRIES + 1):
            # First pass: fast Web Unlocker screenshot. On retry (price still
            # weak), use the Browser API — a real Chromium that waits for JS to
            # render, catching prices the early capture missed.
            use_browser = attempt > 1
            sync_emit(scan_id, "Evidence Vault", "action",
                      f"Capturing rendered screenshot for {state}"
                      + (" via Browser API (full render)" if use_browser else ""), state=state)
            png = brightdata.fetch_screenshot(url, state, prefer_browser=use_browser)
            if png and (best_png is None or len(png) > len(best_png)):
                best_png = png
            # Only bother with vision if the HTML price looked weak.
            if png and _weak():
                if attempt == 1:
                    sync_emit(scan_id, "Vision", "thinking",
                              f"Reading prices from the rendered {state} screenshot (JS-rendered prices)",
                              state=state)
                v = vision.extract_prices(png)
                v_adv = float(v.get("advertised_price") or 0)
                v_fin = float(v.get("final_price") or 0)
                if v_adv > 0 and crawl["advertised_price"] < 5:
                    crawl["advertised_price"] = v_adv
                if v_fin > 0 and journey["final_price"] < 5:
                    journey["final_price"] = v_fin
                if not journey["fees"] and v.get("fees"):
                    from app.agents.types import FeeItem
                    for f in v["fees"]:
                        try:
                            journey["fees"].append(FeeItem(
                                fee_name=str(f.get("fee_name", "fee")),
                                fee_amount=float(f.get("fee_amount") or 0),
                                fee_type=str(f.get("fee_name", "")).split()[0].lower() if f.get("fee_name") else "unknown",
                            ))
                        except Exception:
                            continue
                if v_adv or v_fin:
                    sync_emit(scan_id, "Vision", "result",
                              f"{state}: vision read advertised=${crawl['advertised_price']:.2f} "
                              f"final=${journey['final_price']:.2f} · {len(journey['fees'])} fee(s)"
                              + (f" (attempt {attempt})" if attempt > 1 else ""),
                              state=state, currency=v.get("currency", ""))
            # Stop retrying once we have a price (or HTML was already strong).
            if not _weak():
                break
            if attempt < MAX_SHOT_TRIES and png and _weak():
                sync_emit(scan_id, "Vision", "warn",
                          f"{state}: screenshot likely captured before render finished — recapturing",
                          state=state)
        # Seal the best screenshot we got.
        if best_png:
            shot = storage.store_image(scan_id, state, best_png)
            shot_sha, shot_path = shot.sha256, shot.storage_path
            sync_emit(scan_id, "Evidence Vault", "done",
                      f"{state} screenshot sealed · {len(best_png)//1024} KB · sha256={shot.sha256[:12]}…",
                      state=state, sha256=shot.sha256, storage_path=shot.storage_path)

    # Reconcile when only ONE price was found on the page (e.g. retail product
    # with a single sticker price, no itemised checkout). Without this, the UI
    # shows "advertised $0 / final $X / hidden $X" which is misleading — the
    # page has no hidden fee, just one price.
    adv_in, fin_in = crawl["advertised_price"], journey["final_price"]
    if adv_in == 0 and fin_in > 0 and not journey["fees"]:
        adv_in = fin_in
        sync_emit(scan_id, "Diff", "thinking",
                  f"Single-price page detected for {state} — advertised = final = ${fin_in:.2f}",
                  state=state)
    elif fin_in == 0 and adv_in > 0 and not journey["fees"]:
        fin_in = adv_in
    crawl["advertised_price"] = adv_in
    journey["final_price"] = fin_in

    sync_emit(scan_id, "Diff", "thinking", f"Comparing advertised vs final for {state}", state=state)
    diff = DiffAgent().analyze(crawl["advertised_price"], journey["final_price"], journey["fees"])
    sync_emit(
        scan_id, "Diff", "result",
        f"{state}: ${diff['hidden_total']:.2f} hidden in checkout across "
        f"{len(diff['fees'])} fee(s); "
        f"{sum(1 for f in diff['fees'] if f.is_junk_fee)} likely junk",
        state=state, hidden_total=diff["hidden_total"],
    )

    sync_emit(scan_id, "Law-Mapper", "thinking", f"Mapping fees to FTC clauses for {state}", state=state)
    # Law-Mapper sets the authoritative FTC clause (and can upgrade junk status).
    fees = LawMapperAgent().enrich(diff["fees"])
    sync_emit(
        scan_id, "Law-Mapper", "result",
        f"{state}: {len(fees)} fee(s) classified under 16 CFR Part 464",
        state=state, clauses=list({(f.ftc_clause or "").split(" ", 1)[0] for f in fees if f.ftc_clause})[:4],
    )

    sync_emit(scan_id, "Evidence Vault", "action", f"Sealing HTML snapshot for {state} (SHA-256)", state=state)
    snap = storage.store_snapshot(scan_id, state, journey["html"])
    sync_emit(
        scan_id, "Evidence Vault", "done",
        f"{state} snapshot sealed · sha256={snap.sha256[:12]}…",
        state=state, sha256=snap.sha256, storage_path=snap.storage_path,
    )

    return GeoListing(
        state=state,
        advertised_price=round(crawl["advertised_price"], 2),
        final_price=round(journey["final_price"], 2),
        fees=fees,
        html=journey["html"],
        snapshot_sha256=snap.sha256,
        snapshot_path=snap.storage_path,
        snapshot_url=snap.public_url,
        screenshot_sha256=shot_sha,
        screenshot_path=shot_path,
        source=journey["source"],
        live=journey["live"],
    )


# ── Public entrypoint ─────────────────────────────────────────────────────────

async def run_scan(scan_id: str, url: str, states: list[str] | None = None) -> ScanBrief:
    """Run a full two-geo scan and persist results. Returns the ScanBrief."""
    states = states or settings.default_states
    logger.info("▶ Scan %s starting: %s across %s", scan_id, url, states)
    # Reset event stream so a re-run shows a clean feed.
    try:
        await clear_events(scan_id)
    except Exception:
        pass
    sync_emit(scan_id, "Pipeline", "queued",
              f"Scan accepted · {url} · comparing {', '.join(states)}",
              url=url, states=states)
    await update_scan_status(scan_id, "processing")

    # Recall: have we scanned this operator before? Surface prior intelligence.
    try:
        domain = memory.domain_of(url)
        prior = memory.recall(domain)
        if prior:
            sync_emit(
                scan_id, "Memory", "thinking",
                f"Recall: seen {domain} {prior.get('scan_count', 0)}× before · "
                f"prior fee types: {', '.join(prior.get('fee_types', [])) or 'none'}",
                domain=domain, prior=prior,
            )
    except Exception:
        pass

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

        # Remember this operator's fee patterns for future scans (fire-and-forget;
        # the knowledge-graph enrichment runs in a background thread).
        try:
            fee_types = sorted({f.fee_type for l in brief.listings for f in l.fees if f.fee_type})
            gap = brief.comparison.delta if (brief.comparison and brief.comparison.discrimination_detected) else 0
            memory.record(memory.domain_of(url), {
                "fee_types": fee_types,
                "geo_gap": gap,
                "summary": brief.summary,
            })
        except Exception:
            pass

        sync_emit(scan_id, "Filing", "done",
                  f"Scan complete · {brief.summary}",
                  summary=brief.summary)
        logger.info("✔ Scan %s complete — %s", scan_id, brief.summary)
        return brief
    except Exception as e:
        sync_emit(scan_id, "Pipeline", "error", f"Scan failed: {e}")
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
            sync_emit(scan_id, "Pipeline", "warn",
                      f"{st} hit the {PER_STATE_TIMEOUT}s hard cap — recording empty listing (target likely Cloudflare-protected)",
                      state=st, reason="per_state_timeout", limit_seconds=PER_STATE_TIMEOUT)
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

            # Strip NUL bytes — Postgres TEXT rejects 0x00 (Kayak and some
            # other JS bundles embed binary payloads in the rendered HTML).
            safe_html = (gl.html or "").replace("\x00", "")
            session.add(EvidenceSnapshot(
                scan_id=uuid.UUID(brief.scan_id),
                html_content=safe_html,
                sha256_hash=gl.snapshot_sha256 or "",
                timestamp=datetime.now(timezone.utc),
                storage_path=gl.snapshot_path,
            ))

            # Visual evidence row — screenshot PNG (html_content empty; the
            # storage_path points at the .png so the PDF generator can embed it).
            if gl.screenshot_path:
                session.add(EvidenceSnapshot(
                    scan_id=uuid.UUID(brief.scan_id),
                    html_content="",
                    sha256_hash=gl.screenshot_sha256 or "",
                    timestamp=datetime.now(timezone.utc),
                    storage_path=gl.screenshot_path,
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
