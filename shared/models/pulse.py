import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class PulseAdSnapshot(Base):
    """
    Append-only record of every AdSignal observation captured by pulse.
    AdSignal itself only stores the latest reading (upsert); this table
    accumulates the history that spike detection needs to compare against.
    Written by POST /pulse/snapshot (called after each orbit ad pull).
    """
    __tablename__ = "pulse_ad_snapshots"
    __table_args__ = (
        Index("ix_pulse_snapshots_term_at", "search_term", "snapshotted_at"),
        Index("ix_pulse_snapshots_product_at", "product_id", "snapshotted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Denormalised from AdSignal — kept even if the source row is later deleted
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    search_term: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    ad_count_active: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshotted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PulseAlert(Base):
    """
    Every alert pulse emits, acknowledged or not.
    Kept permanently — used later for threshold tuning and oracle feedback.
    """
    __tablename__ = "pulse_alerts"
    __table_args__ = (
        Index("ix_pulse_alerts_product_id", "product_id"),
        Index("ix_pulse_alerts_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Only "ad_count_spike" for now; extend as more triggers are added
    alert_type: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    search_term: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    baseline_count: Mapped[int] = mapped_column(Integer, nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False)
    spike_ratio: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    threshold_ratio: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    # Deep-link to sentinel search for this product
    sentinel_url: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
