"""
Complaint endpoint - POST /generate-complaint/{scan_id}
Generates a formal complaint document and evidence bundle
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.models.scan import Scan
from app.schemas import ComplaintResponse
from app.services.bundle import generate_bundle

router = APIRouter()


@router.post("/generate-complaint/{scan_id}")
async def generate_complaint_bundle(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Response:
    """
    Generate a class-action evidence bundle ZIP file for a scan
    
    Args:
        scan_id: Unique identifier for the scan
        db: Database session
    
    Returns:
        ZIP file containing scan summary, listings, fees, and evidence snapshots
    
    Raises:
        HTTPException: If scan not found or bundle generation fails
    """
    try:
        # Generate the evidence bundle ZIP
        zip_bytes = await generate_bundle(scan_id, db)
        
        # Return ZIP file as download response
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=evidence_bundle_{scan_id}.zip"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate bundle: {str(e)}")


@router.post("/generate-complaint/{scan_id}/legacy", response_model=ComplaintResponse)
async def generate_complaint(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ComplaintResponse:
    """
    Legacy endpoint - Generate a formal complaint document for a scan
    
    Args:
        scan_id: Unique identifier for the scan
        db: Database session
    
    Returns:
        Complaint response with URL (stub implementation)
    """
    # Verify scan exists
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Stub implementation - returns pending status
    # In production, this would generate a PDF complaint and upload to storage
    return ComplaintResponse(
        complaint_url="pending",
        scan_id=scan_id
    )


# Made with Bob
