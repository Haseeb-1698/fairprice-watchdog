"""Pydantic request/response schemas for the FairPrice Watchdog API."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    url: str = Field(..., description="Listing / checkout URL to scan")
    states: Optional[List[str]] = Field(
        default=None,
        description="US state codes to compare (default: server config, e.g. ['CA','TX'])",
    )


class ScanCreateResponse(BaseModel):
    scan_id: str
    status: str
    url: str


class FeeOut(BaseModel):
    fee_name: str
    fee_amount: float
    fee_type: str
    is_junk_fee: bool
    ftc_clause: Optional[str] = None


class ListingOut(BaseModel):
    id: str
    location_state: str
    advertised_price: float
    final_price: float
    hidden_fee_total: float
    fees: List[FeeOut] = []


class ComparisonOut(BaseModel):
    state_a: str
    state_b: str
    price_a: float
    price_b: float
    delta: float
    pct: float
    higher_state: str
    discrimination_detected: bool


class ResultsResponse(BaseModel):
    scan_id: str
    url: str
    status: str
    created_at: Optional[datetime] = None
    listings: List[ListingOut] = []
    comparison: Optional[ComparisonOut] = None
    summary: str = ""


class EvidenceItem(BaseModel):
    id: str
    state: Optional[str] = None
    sha256_hash: str
    storage_path: Optional[str] = None
    download_url: Optional[str] = None
    timestamp: Optional[datetime] = None


class EvidenceResponse(BaseModel):
    scan_id: str
    snapshots: List[EvidenceItem] = []
