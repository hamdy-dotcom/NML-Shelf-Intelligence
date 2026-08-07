import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class StoreChain(str, enum.Enum):
    panda = "panda"
    othaim = "othaim"


class StoreCluster(Base):
    __tablename__ = "store_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured tiers for oracle/prism consumption — "high" | "mid" | "low"
    income_tier: Mapped[str] = mapped_column(Text, nullable=False)
    footfall_tier: Mapped[str] = mapped_column(Text, nullable=False)
    # GASTAT administrative region code convention (01=Riyadh, 02=Makkah, 04=Eastern, ...)
    region_code: Mapped[str] = mapped_column(Text, nullable=False)
    region_name_ar: Mapped[str] = mapped_column(Text, nullable=False)
    region_name_en: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    # "mock_fixture" until real GASTAT data is loaded; then "gastat_2022" etc.
    data_source: Mapped[str] = mapped_column(Text, nullable=False, default="mock_fixture")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (Index("ix_stores_cluster_id", "cluster_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_ar: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    chain: Mapped[StoreChain] = mapped_column(
        Enum(StoreChain, name="store_chain"), nullable=False
    )
    branch_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    city_ar: Mapped[str] = mapped_column(Text, nullable=False)
    city_en: Mapped[str] = mapped_column(Text, nullable=False)
    region_code: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lon: Mapped[float | None] = mapped_column(Numeric(9, 6))
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("store_clusters.id"), nullable=True
    )
    # Manual override tracking — set when the team corrects an auto-assignment
    cluster_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cluster_override_by: Mapped[str | None] = mapped_column(Text)
    cluster_override_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # "mock_fixture" until real branch data is loaded
    data_source: Mapped[str] = mapped_column(Text, nullable=False, default="mock_fixture")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
