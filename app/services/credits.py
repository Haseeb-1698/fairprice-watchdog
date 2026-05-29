"""
credits.py — Bright Data credit / scan-budget tracker (PRD Risk #3).

Budget: $250 of credits, hard cap of 500 live scans across the whole build.
Each live page fetch / checkout walk costs ~$0.10–$0.30. We meter *live* calls
only (mock costs nothing) and refuse to exceed the cap, falling back to mock.

State is persisted to a small JSON file so the count survives restarts; in a
multi-process deploy point CREDITS_FILE at shared storage or swap for Redis.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_CREDITS_FILE = Path(os.environ.get("CREDITS_FILE", "./.brightdata_credits.json"))
_DEFAULT_COST = float(os.environ.get("BRIGHTDATA_COST_PER_CALL", "0.20"))
_lock = threading.Lock()


@dataclass
class CreditState:
    live_calls: int = 0
    estimated_spend_usd: float = 0.0
    last_call_at: str | None = None


def _load() -> CreditState:
    try:
        if _CREDITS_FILE.exists():
            return CreditState(**json.loads(_CREDITS_FILE.read_text()))
    except Exception as e:
        logger.debug("credits load failed: %s", e)
    return CreditState()


def _save(state: CreditState) -> None:
    try:
        _CREDITS_FILE.write_text(json.dumps(asdict(state), indent=2))
    except Exception as e:
        logger.debug("credits save failed: %s", e)


def can_spend() -> bool:
    """True if we are still under the live-scan cap."""
    with _lock:
        return _load().live_calls < settings.BRIGHTDATA_CREDIT_CAP


def record(cost: float = _DEFAULT_COST) -> CreditState:
    """Record one live call. Returns the updated state."""
    with _lock:
        state = _load()
        state.live_calls += 1
        state.estimated_spend_usd = round(state.estimated_spend_usd + cost, 2)
        state.last_call_at = datetime.now(timezone.utc).isoformat()
        _save(state)
        # Note: NOT calling can_spend() here (it would re-acquire _lock = deadlock).
        # Compute the cap check inline so we still log when budget is near/over.
        over_cap = state.live_calls >= settings.BRIGHTDATA_CREDIT_CAP
        if state.live_calls % 25 == 0 or over_cap:
            logger.warning("Bright Data: %d/%d live calls, ~$%.2f spent",
                           state.live_calls, settings.BRIGHTDATA_CREDIT_CAP, state.estimated_spend_usd)
        return state


def summary() -> dict:
    s = _load()
    return {
        "live_calls": s.live_calls,
        "cap": settings.BRIGHTDATA_CREDIT_CAP,
        "remaining": max(0, settings.BRIGHTDATA_CREDIT_CAP - s.live_calls),
        "estimated_spend_usd": s.estimated_spend_usd,
        "last_call_at": s.last_call_at,
    }
