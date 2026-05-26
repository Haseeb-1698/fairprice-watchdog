"""
EvidenceSnapshot model - Stores HTML snapshots as evidence
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class EvidenceSnapshot(Base):
    """EvidenceSnapshot table - stores HTML evidence snapshots"""
    
    __tablename__ = "evidence_snapshots"
    
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
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    storage_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Relationships
    scan: Mapped["Scan"] = relationship(
        "Scan",
        back_populates="evidence_snapshots"
    )
    
    def __repr__(self) -> str:
        return f"<EvidenceSnapshot(id={self.id}, scan_id={self.scan_id}, sha256_hash={self.sha256_hash[:16]}...)>"

# Made with Bob
