import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class ListingSource(str, enum.Enum):
    salla_api = "salla_api"
    public_listing = "public_listing"
    manual = "manual"


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("store_name", "external_id", name="uq_listing_store_external"),
        Index("ix_listings_product_id", "product_id"),
        Index("ix_listings_scraped_at", "scraped_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable until genome resolves it
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    store_name: Mapped[str] = mapped_column(Text, nullable=False)
    store_url: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)
    gtin: Mapped[str | None] = mapped_column(Text)
    listing_title_raw: Mapped[str] = mapped_column(Text, nullable=False)
    listing_image_url: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="SAR")
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[ListingSource] = mapped_column(
        Enum(ListingSource, name="listing_source"), nullable=False
    )
    # Populated by genome — records which pipeline step resolved product_id
    resolved_by: Mapped[str | None] = mapped_column(Text)
