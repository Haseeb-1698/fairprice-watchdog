"""
Scan endpoint - POST /scan
Initiates a price monitoring scan
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.models.scan import Scan
from app.schemas import ScanCreate, ScanResponse
from app.services.queue import enqueue_scan


# Map the frontend's lowercase names ("california"/"germany"/"gb") to the
# canonical codes the pipeline + Bright Data proxy username use ("CA"/"DE"/"GB").
_NAME_TO_CODE = {
    # US states
    "california": "CA", "texas": "TX", "new york": "NY", "florida": "FL",
    "washington": "WA", "georgia": "GA", "illinois": "IL", "arizona": "AZ",
    "nevada": "NV", "colorado": "CO",
    # Countries
    "united states": "US",
    "united kingdom": "GB", "uk": "GB", "great britain": "GB", "britain": "GB",
    "germany": "DE", "france": "FR", "italy": "IT", "spain": "ES",
    "netherlands": "NL", "belgium": "BE", "poland": "PL", "sweden": "SE",
    "finland": "FI", "denmark": "DK", "ireland": "IE", "portugal": "PT",
    "austria": "AT", "czechia": "CZ", "greece": "GR", "hungary": "HU",
    "romania": "RO", "bulgaria": "BG", "croatia": "HR", "slovakia": "SK",
    "slovenia": "SI", "lithuania": "LT", "latvia": "LV", "estonia": "EE",
    "cyprus": "CY", "malta": "MT", "luxembourg": "LU",
}


def _normalize_geo(g: str) -> str:
    """Accept a name or 2-letter code from any source; return canonical code."""
    s = (g or "").strip()
    if not s:
        return ""
    # 2-letter code as-is
    if len(s) == 2 and s.isalpha():
        return s.upper()
    return _NAME_TO_CODE.get(s.lower(), s.upper())

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
async def create_scan(
    scan_data: ScanCreate,
    db: AsyncSession = Depends(get_db)
) -> ScanResponse:
    """
    Initiate a new price monitoring scan
    
    Args:
        scan_data: Scan configuration with URL and geographic locations
        db: Database session
    
    Returns:
        ScanResponse with scan details
    """
    # Create new scan record in database
    new_scan = Scan(
        id=uuid.uuid4(),
        url=scan_data.url,
        status="queued"
    )
    
    db.add(new_scan)
    # COMMIT FIRST, then enqueue. If we enqueue before committing, the worker
    # can BLPOP the id and look it up before this txn is visible — resulting in
    # "scan has no URL / not found — skipping".
    await db.commit()
    await db.refresh(new_scan)

    # Normalize the geos the frontend sent into canonical codes (CA, TX, GB,
    # DE, etc.) and pass them to the worker — without this the worker reads an
    # empty 'states' field from Redis and falls back to DEFAULT_SCAN_STATES.
    normalized = [c for c in (_normalize_geo(g) for g in (scan_data.geos or [])) if c]
    await enqueue_scan(str(new_scan.id), states=normalized or None)
    
    # Return response with geos from request
    return ScanResponse(
        id=new_scan.id,
        url=new_scan.url,
        status=new_scan.status,
        created_at=new_scan.created_at,
        geos=scan_data.geos
    )


@router.get("/scan/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ScanResponse:
    """
    Get scan status by ID
    
    Args:
        scan_id: Unique identifier for the scan
        db: Database session
    
    Returns:
        ScanResponse with current scan status
    """
    # Query scan from database
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Return response with default geos (since we don't store geos in DB yet)
    return ScanResponse(
        id=scan.id,
        url=scan.url,
        status=scan.status,
        created_at=scan.created_at,
        geos=["california", "texas"]  # Default geos
    )


# Made with Bob
