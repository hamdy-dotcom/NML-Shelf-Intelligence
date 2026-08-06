import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class AdPlatform(str, enum.Enum):
    meta = "meta"
    tiktok = "tiktok"
    snap = "snap"
    google = "google"


class AdSignal(Base):
    __tablename__ = "ad_signals"
    __table_args__ = (
        UniqueConstraint("platform", "search_term", name="uq_ad_signal_platform_term"),
        Index("ix_ad_signals_product_observed", "product_id", "observed_at"),
        Index("ix_ad_signals_listing_id", "listing_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Both nullable — ad signals may arrive before genome links them to a product/listing
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True
    )
    platform: Mapped[AdPlatform] = mapped_column(
        Enum(AdPlatform, name="ad_platform"), nullable=False
    )
    search_term: Mapped[str] = mapped_column(Text, nullable=False)
    ad_count_active: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
