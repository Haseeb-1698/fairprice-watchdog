"""
Evidence service - Handles evidence storage with MinIO and SHA-256 hashing
"""
import hashlib
import uuid
from datetime import datetime
from typing import List
from io import BytesIO

from minio import Minio
from minio.error import S3Error
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.evidence_snapshot import EvidenceSnapshot
from app.schemas import EvidenceSnapshotResponse


# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False  # Set to True if using HTTPS
)


async def ensure_bucket_exists():
    """Ensure the MinIO bucket exists, create if it doesn't"""
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
    except S3Error as e:
        print(f"Error ensuring bucket exists: {e}")
        raise


async def store_evidence(
    scan_id: uuid.UUID,
    html_content: str,
    db: AsyncSession
) -> EvidenceSnapshot:
    """
    Store HTML evidence in MinIO and save metadata to Postgres
    
    Args:
        scan_id: UUID of the scan
        html_content: HTML content to store
        db: Database session
    
    Returns:
        EvidenceSnapshot object with all metadata
    """
    # Ensure bucket exists
    await ensure_bucket_exists()
    
    # Compute SHA-256 hash of html_content
    sha256_hash = hashlib.sha256(html_content.encode('utf-8')).hexdigest()
    
    # Generate timestamp and storage path
    timestamp = datetime.utcnow()
    storage_path = f"{scan_id}/{timestamp.strftime('%Y%m%d_%H%M%S')}.html"
    
    # Store HTML file in MinIO
    try:
        html_bytes = html_content.encode('utf-8')
        html_stream = BytesIO(html_bytes)
        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=storage_path,
            data=html_stream,
            length=len(html_bytes),
            content_type='text/html'
        )
    except S3Error as e:
        print(f"Error storing evidence in MinIO: {e}")
        raise
    
    # Create EvidenceSnapshot record
    evidence_snapshot = EvidenceSnapshot(
        scan_id=scan_id,
        html_content=html_content,
        sha256_hash=sha256_hash,
        timestamp=timestamp,
        storage_path=storage_path
    )
    
    # Save to database
    db.add(evidence_snapshot)
    await db.commit()
    await db.refresh(evidence_snapshot)
    
    return evidence_snapshot


async def get_evidence(
    scan_id: uuid.UUID,
    db: AsyncSession
) -> List[EvidenceSnapshotResponse]:
    """
    Get all evidence snapshots for a scan
    
    Args:
        scan_id: UUID of the scan
        db: Database session
    
    Returns:
        List of EvidenceSnapshotResponse objects
    """
    # Query all evidence snapshots for the scan
    result = await db.execute(
        select(EvidenceSnapshot)
        .where(EvidenceSnapshot.scan_id == scan_id)
        .order_by(EvidenceSnapshot.timestamp.desc())
    )
    snapshots = result.scalars().all()
    
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