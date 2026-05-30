"""
Screenshot serving — exposes the captured page screenshots to the UI so the
results screen can show both locations' captures side-by-side (the same images
that are sealed in the evidence vault + embedded in the PDF complaint).

GET /api/screenshot/{scan_id}/{state}   — returns the PNG for that scan+state
GET /api/screenshots/{scan_id}          — lists which states have a screenshot
"""
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.database import get_db
from app.models.evidence_snapshot import EvidenceSnapshot

router = APIRouter()


def _load_bytes(storage_path: str) -> bytes | None:
    """Load image bytes from a file:// or s3:// storage path."""
    if not storage_path:
        return None
    try:
        if storage_path.startswith("file://"):
            import os
            from urllib.parse import urlparse, unquote
            p = unquote(urlparse(storage_path).path)
            if os.name == "nt" and p.startswith("/") and len(p) > 2 and p[2] == ":":
                p = p[1:]
            with open(p, "rb") as f:
                return f.read()
        if storage_path.startswith("s3://"):
            from app.services import storage as _storage
            client = _storage._get_client()
            if client is None:
                return None
            _, _, rest = storage_path.partition("s3://")
            bucket, _, key = rest.partition("/")
            return client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception:
        return None
    return None


async def _find_screenshot(scan_id: uuid.UUID, state: str, db: AsyncSession) -> str | None:
    """Find the screenshot storage_path for a scan+state (path is .../{state}/...png)."""
    res = await db.execute(
        select(EvidenceSnapshot).where(EvidenceSnapshot.scan_id == scan_id)
    )
    state_l = f"/{state.lower()}/"
    for snap in res.scalars().all():
        sp = (snap.storage_path or "")
        if sp.lower().endswith((".png", ".jpg", ".jpeg")) and state_l in sp.lower():
            return sp
    return None


@router.get("/screenshots/{scan_id}")
async def list_screenshots(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """Return the states that have a screenshot available for this scan."""
    res = await db.execute(
        select(EvidenceSnapshot).where(EvidenceSnapshot.scan_id == scan_id)
    )
    states = []
    for snap in res.scalars().all():
        sp = (snap.storage_path or "")
        if sp.lower().endswith((".png", ".jpg", ".jpeg")):
            # path is {scan_id}/{state}/checkout-...png
            parts = sp.rstrip("/").split("/")
            if len(parts) >= 2:
                states.append({"state": parts[-2].upper(), "sha256": snap.sha256_hash})
    return {"scan_id": str(scan_id), "screenshots": states}


@router.get("/screenshot/{scan_id}/{state}")
async def get_screenshot(scan_id: uuid.UUID, state: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Serve the captured screenshot PNG for a scan+state."""
    path = await _find_screenshot(scan_id, state, db)
    if not path:
        raise HTTPException(status_code=404, detail="no screenshot for this scan/state")
    data = _load_bytes(path)
    if not data:
        raise HTTPException(status_code=404, detail="screenshot file unavailable")
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"})
