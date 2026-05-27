"""
Background worker — consumes the Redis scan queue and runs the agent pipeline.

Loop: BLPOP scan_queue → load the scan's URL + requested states → run the
two-geo pipeline (Crawler → Journey → Diff → evidence vault) → persist results.
"""
import asyncio
import logging
import uuid

import redis.asyncio as aioredis

from app.agents import pipeline
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.scan import Scan
from app.services.queue import get_scan_states

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _load_scan(scan_id: str):
    """Fetch the scan's URL from Postgres."""
    async with AsyncSessionLocal() as session:
        scan = await session.get(Scan, uuid.UUID(scan_id))
        return scan.url if scan else None


async def _handle(scan_id: str) -> None:
    url = await _load_scan(scan_id)
    if not url:
        logger.warning("Scan %s has no URL / not found — skipping", scan_id)
        return
    states = await get_scan_states(scan_id) or settings.default_states
    try:
        await pipeline.run_scan(scan_id, url, states)
    except Exception as e:
        logger.exception("Pipeline failed for scan %s: %s", scan_id, e)


async def process_tasks() -> None:
    logger.info("🚀 Starting FairPrice Watchdog worker...")
    logger.info("📊 Redis: %s", settings.REDIS_URL)
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        await redis.ping()
        logger.info("✅ Redis connection successful")
    except Exception as e:
        logger.error("❌ Redis connection failed: %s", e)
        return

    logger.info("⏳ Waiting for scan jobs on 'scan_queue'...")
    while True:
        try:
            item = await redis.blpop("scan_queue", timeout=5)
            if item is None:
                continue
            _, scan_id = item
            logger.info("📥 Picked up scan %s", scan_id)
            await _handle(scan_id)
        except asyncio.CancelledError:
            logger.info("🛑 Worker shutting down...")
            break
        except Exception as e:
            logger.error("❌ Error in worker loop: %s", e)
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(process_tasks())
