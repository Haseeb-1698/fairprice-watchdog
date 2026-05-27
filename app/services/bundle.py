"""
Bundle service - Generate class-action evidence bundle ZIP files
"""
import json
import hashlib
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.scan import Scan
from app.models.listing import Listing
from app.models.fee import Fee
from app.models.evidence_snapshot import EvidenceSnapshot


async def generate_bundle(scan_id: uuid.UUID, db: AsyncSession) -> bytes:
    """
    Generate a class-action evidence bundle ZIP file
    
    Args:
        scan_id: UUID of the scan to bundle
        db: Database session
    
    Returns:
        ZIP file as bytes
    
    Raises:
        ValueError: If scan not found
    """
    # Fetch scan with all related data
    result = await db.execute(
        select(Scan)
        .options(
            selectinload(Scan.listings).selectinload(Listing.fees),
            selectinload(Scan.evidence_snapshots)
        )
        .where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise ValueError(f"Scan {scan_id} not found")
    
    # Create in-memory ZIP file
    zip_buffer = BytesIO()
    manifest_data: Dict[str, str] = {}
    
    with ZipFile(zip_buffer, 'w', ZIP_DEFLATED) as zip_file:
        # 1. Generate scan_summary.json
        scan_summary = {
            "scan": {
                "id": str(scan.id),
                "url": scan.url,
                "status": scan.status,
                "created_at": scan.created_at.isoformat(),
                "updated_at": scan.updated_at.isoformat()
            },
            "listings": [],
            "total_listings": len(scan.listings),
            "total_evidence_snapshots": len(scan.evidence_snapshots)
        }
        
        # Add listings with fees
        for listing in scan.listings:
            listing_data = {
                "id": str(listing.id),
                "advertised_price": listing.advertised_price,
                "final_price": listing.final_price,
                "location_state": listing.location_state,
                "created_at": listing.created_at.isoformat(),
                "fees": []
            }
            
            for fee in listing.fees:
                fee_data = {
                    "id": str(fee.id),
                    "fee_name": fee.fee_name,
                    "fee_amount": fee.fee_amount,
                    "fee_type": fee.fee_type,
                    "is_junk_fee": fee.is_junk_fee,
                    "ftc_clause": fee.ftc_clause,
                    "created_at": fee.created_at.isoformat()
                }
                listing_data["fees"].append(fee_data)
            
            scan_summary["listings"].append(listing_data)
        
        # Write scan_summary.json to ZIP
        summary_json = json.dumps(scan_summary, indent=2)
        zip_file.writestr("scan_summary.json", summary_json)
        
        # Calculate SHA256 hash for scan_summary.json
        summary_hash = hashlib.sha256(summary_json.encode()).hexdigest()
        manifest_data["scan_summary.json"] = summary_hash
        
        # 2. Add evidence snapshots as HTML files
        for snapshot in scan.evidence_snapshots:
            snapshot_filename = f"evidence/{snapshot.id}.html"
            zip_file.writestr(snapshot_filename, snapshot.html_content)
            
            # Use existing SHA256 hash from database
            manifest_data[snapshot_filename] = snapshot.sha256_hash
        
        # 3. Generate manifest.json with SHA256 hashes
        manifest_json = json.dumps(manifest_data, indent=2)
        zip_file.writestr("manifest.json", manifest_json)
    
    # Return ZIP file bytes
    zip_buffer.seek(0)
    return zip_buffer.read()


# Made with Bob