"""
Results endpoint - GET /results/{id}
Returns scan results: per-state listings, fees, and the two-geo comparison.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.listing import Listing
from app.models.scan import Scan
from app.schemas import ComparisonOut, FeeOut, ListingOut, ResultsResponse

router = APIRouter()


def _comparison(listings: list[Listing]) -> ComparisonOut | None:
    if len(listings) < 2:
        return None
    a, b = listings[0], listings[1]
    delta = round(abs(a.final_price - b.final_price), 2)
    low = min(a.final_price, b.final_price) or 1.0
    higher = a.location_state if a.final_price >= b.final_price else b.location_state
    return ComparisonOut(
        state_a=a.location_state, price_a=round(a.final_price, 2),
        state_b=b.location_state, price_b=round(b.final_price, 2),
        delta=delta, pct=round(delta / low * 100, 1),
        higher_state=higher, discrimination_detected=delta >= 1.0,
    )


@router.get("/results/{result_id}", response_model=ResultsResponse)
async def get_results(result_id: str, db: AsyncSession = Depends(get_db)) -> ResultsResponse:
    """Get scan results by ID, including listings, fees, and geo comparison."""
    try:
        scan_uuid = uuid.UUID(result_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan id")

    scan = await db.get(Scan, scan_uuid)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    rows = await db.execute(
        select(Listing)
        .where(Listing.scan_id == scan_uuid)
        .options(selectinload(Listing.fees))
        .order_by(Listing.created_at)
    )
    listings = list(rows.scalars().all())

    listings_out = [
        ListingOut(
            id=str(l.id),
            location_state=l.location_state,
            advertised_price=round(l.advertised_price, 2),
            final_price=round(l.final_price, 2),
            hidden_fee_total=round(l.final_price - l.advertised_price, 2),
            fees=[
                FeeOut(
                    fee_name=f.fee_name, fee_amount=f.fee_amount, fee_type=f.fee_type,
                    is_junk_fee=f.is_junk_fee, ftc_clause=f.ftc_clause,
                )
                for f in l.fees
            ],
        )
        for l in listings
    ]

    comparison = _comparison(listings)
    summary = ""
    if comparison and comparison.discrimination_detected:
        summary = (
            f"Same listing: {comparison.higher_state} "
            f"${max(comparison.price_a, comparison.price_b):.2f} vs "
            f"${min(comparison.price_a, comparison.price_b):.2f} — "
            f"${comparison.delta:.2f} ({comparison.pct}%) geo gap."
        )

    return ResultsResponse(
        scan_id=result_id,
        url=scan.url,
        status=scan.status,
        created_at=scan.created_at,
        listings=listings_out,
        comparison=comparison,
        summary=summary,
    )
