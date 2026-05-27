"""
Evidence endpoint - GET /evidence/{scan_id}
Retrieves evidence data by scan ID
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.core.database import get_db
from app.models.evidence_snapshot import EvidenceSnapshot
from app.schemas import EvidenceSnapshotResponse

router = APIRouter()


@router.get("/evidence/{scan_id}", response_model=List[EvidenceSnapshotResponse])
async def get_evidence(
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
    # Query all evidence snapshots for the scan
    result = await db.execute(
        select(EvidenceSnapshot)
        .where(EvidenceSnapshot.scan_id == scan_id)
        .order_by(EvidenceSnapshot.timestamp.desc())
    )
    snapshots = result.scalars().all()
    
    if not snapshots:
        # Return empty list if no evidence found (not an error)
        return []
    
    # Convert to response models
    return [
        EvidenceSnapshotResponse(
            id=snapshot.id,
            scan_id=snapshot.scan_id,
            html_content=snapshot.html_content,
            sha256_hash=snapshot.sha256_hash,
            timestamp=snapshot.timestamp,
            storage_path=snapshot.storage_path
        )
        for snapshot in snapshots
    ]


# Made with Bob
