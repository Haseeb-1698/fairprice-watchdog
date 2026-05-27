"""
Evidence endpoints - Store and retrieve evidence snapshots
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas import EvidenceSnapshotResponse
from app.services.evidence import store_evidence, get_evidence as get_evidence_service

router = APIRouter()


class StoreEvidenceRequest(BaseModel):
    """Request body for storing evidence"""
    html_content: str


@router.get("/evidence/{scan_id}", response_model=List[EvidenceSnapshotResponse])
async def get_evidence_endpoint(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[EvidenceSnapshotResponse]:
    """
    Get evidence snapshots for a scan
    
    Args:
        scan_id: Unique identifier for the scan
        db: Database session
    
    Returns:
        List of evidence snapshots for the scan
    """
    return await get_evidence_service(scan_id, db)


@router.post("/evidence/{scan_id}", response_model=EvidenceSnapshotResponse)
async def store_evidence_endpoint(
    scan_id: uuid.UUID,
    request: StoreEvidenceRequest,
    db: AsyncSession = Depends(get_db)
) -> EvidenceSnapshotResponse:
    """
    Store HTML evidence for a scan
    
    Args:
        scan_id: Unique identifier for the scan
        request: Request body containing html_content
        db: Database session
    
    Returns:
        Created evidence snapshot
    """
    try:
        snapshot = await store_evidence(scan_id, request.html_content, db)
        
        return EvidenceSnapshotResponse(
            id=snapshot.id,
            scan_id=snapshot.scan_id,
            html_content=snapshot.html_content,
            sha256_hash=snapshot.sha256_hash,
            timestamp=snapshot.timestamp,
            storage_path=snapshot.storage_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store evidence: {str(e)}"
        )


# Made with Bob
