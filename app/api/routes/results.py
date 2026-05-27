"""
Results endpoint - GET /results/{scan_id}
Retrieves scan results by ID
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from app.core.database import get_db
from app.models.scan import Scan
from app.models.listing import Listing
from app.models.fee import Fee
from app.schemas import (
    ScanResultsResponse,
    ScanResponse,
    ListingWithFeesResponse,
    FeeResponse
)

router = APIRouter()


@router.get("/results/{scan_id}", response_model=ScanResultsResponse)
async def get_results(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ScanResultsResponse:
    """
    Get scan results by ID including all listings and fees
    
    Args:
        scan_id: Unique identifier for the scan
        db: Database session
    
    Returns:
        Complete scan results with listings and fees
    """
    # Query scan with eager loading of listings and fees
    result = await db.execute(
        select(Scan)
        .options(
            selectinload(Scan.listings).selectinload(Listing.fees)
        )
        .where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Build scan response
    scan_response = ScanResponse(
        id=scan.id,
        url=scan.url,
        status=scan.status,
        created_at=scan.created_at,
        geos=["california", "texas"]  # Default geos
    )
    
    # Build listings with fees
    listings_with_fees = []
    for listing in scan.listings:
        fees = [
            FeeResponse(
                id=fee.id,
                listing_id=fee.listing_id,
                fee_name=fee.fee_name,
                fee_amount=fee.fee_amount,
                fee_type=fee.fee_type,
                is_junk_fee=fee.is_junk_fee,
                ftc_clause=fee.ftc_clause,
                created_at=fee.created_at
            )
            for fee in listing.fees
        ]
        
        listings_with_fees.append(
            ListingWithFeesResponse(
                id=listing.id,
                scan_id=listing.scan_id,
                advertised_price=listing.advertised_price,
                final_price=listing.final_price,
                location_state=listing.location_state,
                created_at=listing.created_at,
                fees=fees
            )
        )
    
    return ScanResultsResponse(
        scan=scan_response,
        listings=listings_with_fees
    )


# Made with Bob
