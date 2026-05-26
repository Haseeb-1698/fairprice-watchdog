"""
Listing model - Represents a product listing with pricing information
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Listing(Base):
    """Listing table - tracks individual product listings"""
    
    __tablename__ = "listings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False
    )
    advertised_price: Mapped[float] = mapped_column(Float, nullable=False)
    final_price: Mapped[float] = mapped_column(Float, nullable=False)
    location_state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    scan: Mapped["Scan"] = relationship(
        "Scan",
        back_populates="listings"
    )
    fees: Mapped[List["Fee"]] = relationship(
        "Fee",
        back_populates="listing",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Listing(id={self.id}, advertised_price={self.advertised_price}, final_price={self.final_price})>"

# Made with Bob
