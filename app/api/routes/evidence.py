"""
Evidence endpoint - GET /evidence/{scan_id}
Returns the timestamped, SHA-256-hashed HTML snapshots for a scan, with
presigned download URLs from the evidence vault (MinIO / R2).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.evidence_snapshot import EvidenceSnapshot
from app.schemas import EvidenceItem, EvidenceResponse
from app.services import storage

router = APIRouter()


def _key_from_path(storage_path: str | None) -> str | None:
    """Recover the object key (bucket-relative) from an s3:// storage path."""
    if not storage_path or not storage_path.startswith("s3://"):
        return None
    # s3://<bucket>/<key...>
    rest = storage_path[len("s3://"):]
    return rest.split("/", 1)[1] if "/" in rest else None


@router.get("/evidence/{scan_id}", response_model=EvidenceResponse)
async def get_evidence(scan_id: str, db: AsyncSession = Depends(get_db)) -> EvidenceResponse:
    """Get evidence snapshots (with download URLs) for a scan."""
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan id")

    rows = await db.execute(
        select(EvidenceSnapshot).where(EvidenceSnapshot.scan_id == scan_uuid)
    )
    snapshots = list(rows.scalars().all())

    items = []
    for s in snapshots:
        key = _key_from_path(s.storage_path)
        # Object key layout is {scan_id}/{state}/...; recover state for display.
        state = None
        if key and "/" in key:
            parts = key.split("/")
            state = parts[1] if len(parts) > 1 else None
        items.append(EvidenceItem(
            id=str(s.id),
            state=state,
            sha256_hash=s.sha256_hash,
            storage_path=s.storage_path,
            download_url=storage.presigned_url(key) if key else None,
            timestamp=s.timestamp,
        ))

    return EvidenceResponse(scan_id=scan_id, snapshots=items)
