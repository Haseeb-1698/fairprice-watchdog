"""
Events endpoint — drives the studio-style live agent thinking feed.

GET /api/scan/{scan_id}/events?since=N  — incremental fetch (returns events
starting at offset N). The frontend polls this every ~1s during the running
phase and renders each event as a timeline row.
"""
from fastapi import APIRouter, Query

from app.services.events import list_events

router = APIRouter()


@router.get("/scan/{scan_id}/events")
async def get_scan_events(scan_id: str, since: int = Query(0, ge=0), limit: int = Query(200, ge=1, le=500)):
    events = await list_events(scan_id, since=since, limit=limit)
    return {
        "scan_id": scan_id,
        "since": since,
        "count": len(events),
        "events": events,
        "next_since": since + len(events),
    }
