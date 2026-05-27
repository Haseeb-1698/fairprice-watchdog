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
    await db.flush()  # Flush to get the ID without committing
    
    # Enqueue scan job to Redis
    await enqueue_scan(str(new_scan.id))
    
    # Commit the transaction
    await db.commit()
    await db.refresh(new_scan)
    
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
