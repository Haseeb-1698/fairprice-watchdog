"""
Pydantic request/response schemas
"""
from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field


class ScanCreate(BaseModel):
    """Schema for creating a new scan"""
    url: str = Field(..., description="URL to scan for pricing information")
    geos: List[str] = Field(
        default=["california", "texas"],
        description="List of geographic locations to scan"
    )


class ScanResponse(BaseModel):
    """Schema for scan response"""
    id: UUID = Field(..., description="Unique scan identifier")
    url: str = Field(..., description="URL being scanned")
    status: str = Field(..., description="Current scan status")
    created_at: datetime = Field(..., description="Timestamp when scan was created")
    geos: List[str] = Field(..., description="Geographic locations being scanned")
    
    class Config:
        from_attributes = True


class ListingResponse(BaseModel):
    """Schema for listing response"""
    id: UUID
    scan_id: UUID
    advertised_price: float
    final_price: float
    location_state: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeeResponse(BaseModel):
    """Schema for fee response"""
    id: UUID
    listing_id: UUID
    fee_name: str
    fee_amount: float
    fee_type: str
    is_junk_fee: bool
    ftc_clause: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ListingWithFeesResponse(BaseModel):
    """Schema for listing with associated fees"""
    id: UUID
    scan_id: UUID
    advertised_price: float
    final_price: float
    location_state: str
    created_at: datetime
    fees: List[FeeResponse] = []
    
    class Config:
        from_attributes = True


class ScanResultsResponse(BaseModel):
    """Schema for complete scan results"""
    scan: ScanResponse
    listings: List[ListingWithFeesResponse] = []
    
    class Config:
        from_attributes = True


class EvidenceSnapshotResponse(BaseModel):
    """Schema for evidence snapshot response"""
    id: UUID
    scan_id: UUID
    html_content: str
    sha256_hash: str
    timestamp: datetime
    storage_path: Optional[str] = None
    
    class Config:
        from_attributes = True


class ComplaintResponse(BaseModel):
    """Schema for complaint generation response"""
    complaint_url: str
    scan_id: UUID


# Made with Bob
