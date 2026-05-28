"""
Redis Queue Service for managing scan jobs
"""
import json
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings


# Redis client instance
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Get or create Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


async def enqueue_scan(scan_id: str, states: Optional[list] = None) -> bool:
    """
    Enqueue a scan job to Redis queue

    Args:
        scan_id: UUID of the scan to enqueue
        states: optional list of US state codes to compare for this scan

    Returns:
        bool: True if successfully enqueued
    """
    redis = await get_redis_client()

    # Add to scan queue
    await redis.lpush("scan_queue", scan_id)  # type: ignore

    # Set initial status + requested states
    await redis.hset(f"scan:{scan_id}", "status", "queued")  # type: ignore
    await redis.hset(f"scan:{scan_id}", "states", json.dumps(states or []))  # type: ignore

    return True


async def get_scan_states(scan_id: str) -> list:
    """Return the requested state codes for a scan (empty list if none set)."""
    redis = await get_redis_client()
    raw = await redis.hget(f"scan:{scan_id}", "states")  # type: ignore
    try:
        return json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []


async def get_scan_status(scan_id: str) -> Optional[str]:
    """
    Get the current status of a scan
    
    Args:
        scan_id: UUID of the scan
        
    Returns:
        Optional[str]: Current status or None if not found
    """
    redis = await get_redis_client()
    status = await redis.hget(f"scan:{scan_id}", "status")  # type: ignore
    return status  # type: ignore


async def update_scan_status(scan_id: str, status: str) -> bool:
    """
    Update the status of a scan
    
    Args:
        scan_id: UUID of the scan
        status: New status (e.g., 'queued', 'processing', 'completed', 'failed')
        
    Returns:
        bool: True if successfully updated
    """
    redis = await get_redis_client()
    await redis.hset(f"scan:{scan_id}", "status", status)  # type: ignore
    return True


async def close_redis_connection():
    """
    Close Redis connection (call on app shutdown)
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()  # type: ignore
        _redis_client = None


# ── Hunt queue helpers ────────────────────────────────────────────────────────

async def enqueue_hunt(hunt_id: str) -> bool:
    """Push hunt_id to the hunt_queue for the worker to pick up."""
    redis = await get_redis_client()
    await redis.lpush("hunt_queue", hunt_id)  # type: ignore
    return True


# Made with Bob