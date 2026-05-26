"""
Complaint model - Represents generated complaint documents
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Complaint(Base):
    """Complaint table - tracks generated complaint documents"""
    
    __tablename__ = "complaints"
    
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
    complaint_type: Mapped[str] = mapped_column(String, nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    scan: Mapped["Scan"] = relationship(
        "Scan",
        back_populates="complaints"
    )
    
    def __repr__(self) -> str:
        return f"<Complaint(id={self.id}, complaint_type={self.complaint_type}, status={self.status})>"

# Made with Bob
