"""
events.py — agent-event stream for the live "studio" thinking feed.

Every agent emits structured events (started/thinking/fetched/extracted/done/error)
that the UI subscribes to during a scan or hunt. Events live in a Redis list
keyed by scan-id so the frontend can poll them incrementally.

Public surface:
    emit(scan_id, agent, level, message, **data)
    sync_emit(scan_id, agent, level, message, **data)   # safe from any thread
    list_events(scan_id, since=0)
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any

import redis as redis_sync
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_KEY = "scan:{scan_id}:events"
_TTL_SECONDS = 24 * 3600
_MAX_PER_SCAN = 200

# Levels — used by the UI to colour rows. "thinking" = LLM is reasoning;
# "action" = a real network/IO step; "result" = a value found; "warn"/"error" = trouble.
LEVELS = ("queued", "started", "thinking", "action", "result", "warn", "error", "done")

# Sync client cache (one connection, reused).
_sync_client: redis_sync.Redis | None = None
_lock = threading.Lock()


def _sync() -> redis_sync.Redis:
    global _sync_client
    if _sync_client is None:
        with _lock:
            if _sync_client is None:
                _sync_client = redis_sync.from_url(settings.REDIS_URL, decode_responses=True)
    return _sync_client


def _make_event(agent: str, level: str, message: str, data: dict | None = None) -> str:
    return json.dumps({
        "ts": int(time.time() * 1000),
        "agent": agent,
        "level": level if level in LEVELS else "action",
        "message": message,
        "data": data or {},
    })


def sync_emit(scan_id: str, agent: str, level: str, message: str, **data: Any) -> None:
    """Thread-safe synchronous emit — call from any agent code path."""
    try:
        r = _sync()
        key = _KEY.format(scan_id=scan_id)
        r.rpush(key, _make_event(agent, level, message, data or None))
        r.ltrim(key, -_MAX_PER_SCAN, -1)
        r.expire(key, _TTL_SECONDS)
    except Exception as e:
        logger.debug("event emit failed (%s): %s/%s/%s", e, agent, level, message)


# Async variants (kept for use from async code paths).
_async_client: aioredis.Redis | None = None


async def _aio() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _async_client


async def emit(scan_id: str, agent: str, level: str, message: str, **data: Any) -> None:
    """Async emit — use from async code; falls through to sync if needed."""
    try:
        r = await _aio()
        key = _KEY.format(scan_id=scan_id)
        await r.rpush(key, _make_event(agent, level, message, data or None))
        await r.ltrim(key, -_MAX_PER_SCAN, -1)
        await r.expire(key, _TTL_SECONDS)
    except Exception as e:
        logger.debug("async event emit failed (%s): %s/%s/%s", e, agent, level, message)


async def list_events(scan_id: str, since: int = 0, limit: int = 200) -> list[dict]:
    """Return events for a scan, newest first by default, ordered by ts ASC.
    `since` skips the first N (so the UI can fetch incrementally)."""
    r = await _aio()
    key = _KEY.format(scan_id=scan_id)
    raw = await r.lrange(key, since, since + limit - 1)
    out: list[dict] = []
    for s in raw:
        try:
            out.append(json.loads(s))
        except Exception:
            continue
    return out


async def clear(scan_id: str) -> None:
    r = await _aio()
    await r.delete(_KEY.format(scan_id=scan_id))
