import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base

TEXT_EMBEDDING_DIM = 768  # intfloat/multilingual-e5-base; must match genome's model output dim


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name_ar: Mapped[str | None] = mapped_column(Text)
    canonical_name_en: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    subcategory: Mapped[str | None] = mapped_column(Text)
    gtin: Mapped[str | None] = mapped_column(Text)
    primary_image_url: Mapped[str | None] = mapped_column(Text)
    # Set by genome step 2; genome step 3 will add image_embedding in a later migration
    text_embedding: Mapped[Any | None] = mapped_column(Vector(TEXT_EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
