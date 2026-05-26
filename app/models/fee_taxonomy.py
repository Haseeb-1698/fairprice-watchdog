"""
FeeTaxonomy model - Fee classification with vector embeddings
"""
import uuid
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class FeeTaxonomy(Base):
    """FeeTaxonomy table - fee classification with semantic embeddings"""
    
    __tablename__ = "fee_taxonomy"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    fee_type: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    ftc_clause: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(384),
        nullable=True
    )
    
    def __repr__(self) -> str:
        return f"<FeeTaxonomy(id={self.id}, fee_type={self.fee_type})>"

# Made with Bob
