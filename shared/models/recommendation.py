import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class RecommendationType(str, enum.Enum):
    genome_match = "genome_match"
    oracle_pick = "oracle_pick"
    prism_price = "prism_price"


class RecommendationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    edited = "edited"


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_listing_id", "listing_id"),
        Index("ix_recommendations_product_id", "product_id"),
        Index("ix_recommendations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType, name="recommendation_type"), nullable=False
    )
    # Nullable — genome matches are not tied to a physical shelf slot
    shelf_slot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True
    )
    # Interpretation depends on type:
    #   genome_match  → str(product_id) being recommended as the match
    #   oracle_pick   → str(product_id) recommended for the shelf slot
    #   prism_price   → SAR price as a string
    recommended_value: Mapped[str | None] = mapped_column(Text)
    reasoning_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status"),
        nullable=False,
        default=RecommendationStatus.pending,
    )
    edited_value: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
