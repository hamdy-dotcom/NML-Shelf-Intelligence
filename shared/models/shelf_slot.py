import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class SlotStatus(str, enum.Enum):
    open = "open"
    filled = "filled"


class ShelfSlot(Base):
    """
    A buyer's intent: one open slot at a specific store, for a specific category.
    Oracle ranks candidate products against this slot and writes its picks to
    ledger.Recommendation with type='oracle_pick'.
    """
    __tablename__ = "shelf_slots"
    __table_args__ = (
        Index("ix_shelf_slots_store_id", "store_id"),
        Index("ix_shelf_slots_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False
    )
    # Free-text category the buyer wants to fill (e.g. "food", "dairy", "personal care")
    # Used to filter candidate products; oracle falls back to all resolved products if
    # no products with a matching category exist yet (products.category is often NULL until
    # real category data is loaded).
    category: Mapped[str] = mapped_column(Text, nullable=False)
    open_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus, name="slot_status"), nullable=False, default=SlotStatus.open
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set when the ledger reviewer approves an oracle pick for this slot
    filled_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
