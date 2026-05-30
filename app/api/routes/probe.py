"""
Probe endpoint — fast geo price-discrimination check.

GET /api/probe?q=...   — searches the query biased to several countries and
                        returns the price split each shopper is shown (~3s).
"""
from fastapi import APIRouter, Query

from app.services import price_probe

router = APIRouter()


@router.get("/probe")
async def price_discrimination_probe(q: str = Query(..., min_length=2)) -> dict:
    return price_probe.probe(q)
