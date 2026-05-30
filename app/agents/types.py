"""
types.py — structured data passed between agents.

These dataclasses are the contract between Crawler → Journey → Diff → pipeline,
and they map cleanly onto Eman's DB models (Listing, Fee, EvidenceSnapshot).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeeItem:
    """One line-item fee discovered in the checkout funnel."""
    fee_name: str
    fee_amount: float
    fee_type: str = "unknown"
    is_junk_fee: bool = False
    ftc_clause: Optional[str] = None
    # agent-clean | partial | na  (na = government charge, excluded from junk total)
    detectability: str = "partial"


@dataclass
class GeoListing:
    """A single listing as seen from one US state."""
    state: str
    advertised_price: float
    final_price: float
    fees: list[FeeItem] = field(default_factory=list)
    html: str = ""
    snapshot_sha256: Optional[str] = None
    snapshot_path: Optional[str] = None
    snapshot_url: Optional[str] = None
    # Visual evidence — full-page screenshot PNG, sealed with its own SHA-256.
    screenshot_sha256: Optional[str] = None
    screenshot_path: Optional[str] = None
    source: str = "mock"            # residential | web_unlocker | browser_api | mock
    live: bool = False

    @property
    def total_fees(self) -> float:
        return round(sum(f.fee_amount for f in self.fees), 2)

    @property
    def junk_fee_total(self) -> float:
        return round(sum(f.fee_amount for f in self.fees if f.is_junk_fee), 2)


@dataclass
class GeoComparison:
    """The two-state price split — the demo punchline."""
    state_a: str
    price_a: float
    state_b: str
    price_b: float

    @property
    def delta(self) -> float:
        return round(abs(self.price_a - self.price_b), 2)

    @property
    def pct(self) -> float:
        low = min(self.price_a, self.price_b) or 1.0
        return round(self.delta / low * 100, 1)

    @property
    def higher_state(self) -> str:
        return self.state_a if self.price_a >= self.price_b else self.state_b

    @property
    def discrimination_detected(self) -> bool:
        return self.delta >= 1.0


@dataclass
class ScanBrief:
    """Everything the pipeline produces for one scan."""
    scan_id: str
    url: str
    listings: list[GeoListing] = field(default_factory=list)
    comparison: Optional[GeoComparison] = None
    summary: str = ""
