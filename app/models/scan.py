"""
Scan model - Represents a price monitoring scan
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Scan(Base):
    """Scan table - tracks price monitoring scans"""
    
    __tablename__ = "scans"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    listings: Mapped[List["Listing"]] = relationship(
        "Listing",
        back_populates="scan",
        cascade="all, delete-orphan"
    )
    evidence_snapshots: Mapped[List["EvidenceSnapshot"]] = relationship(
        "EvidenceSnapshot",
        back_populates="scan",
        cascade="all, delete-orphan"
    )
    complaints: Mapped[List["Complaint"]] = relationship(
        "Complaint",
        back_populates="scan",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, url={self.url}, status={self.status})>"

# Made with Bob
