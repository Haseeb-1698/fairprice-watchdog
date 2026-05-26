"""
Scan endpoint - POST /scan
Creates a scan record and enqueues it for the agent pipeline worker.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.scan import Scan
from app.schemas import ScanCreateResponse, ScanRequest
from app.services.queue import enqueue_scan

router = APIRouter()


@router.post("/scan", response_model=ScanCreateResponse)
async def create_scan(payload: ScanRequest, db: AsyncSession = Depends(get_db)) -> ScanCreateResponse:
    """
    Initiate a new price-monitoring scan.

    Creates a `scans` row (status=queued), pushes the id onto the Redis
    `scan_queue`, and returns immediately. The worker picks it up and runs the
    two-geo agent pipeline, persisting listings / fees / evidence.
    """
    scan = Scan(url=payload.url, status="queued")
    db.add(scan)
    await db.flush()          # populate scan.id
    scan_id = str(scan.id)

    # Stash requested states (if any) alongside the queue entry.
    await enqueue_scan(scan_id, states=payload.states)

    return ScanCreateResponse(scan_id=scan_id, status="queued", url=payload.url)
