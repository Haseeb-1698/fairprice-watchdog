"""
Fee model - Represents individual fees associated with listings
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Fee(Base):
    """Fee table - tracks individual fees on listings"""
    
    __tablename__ = "fees"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False
    )
    fee_name: Mapped[str] = mapped_column(String, nullable=False)
    fee_amount: Mapped[float] = mapped_column(Float, nullable=False)
    fee_type: Mapped[str] = mapped_column(String, nullable=False)
    is_junk_fee: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ftc_clause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    listing: Mapped["Listing"] = relationship(
        "Listing",
        back_populates="fees"
    )
    
    def __repr__(self) -> str:
        return f"<Fee(id={self.id}, fee_name={self.fee_name}, fee_amount={self.fee_amount}, is_junk_fee={self.is_junk_fee})>"

# Made with Bob
