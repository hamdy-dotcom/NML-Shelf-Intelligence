"""Genome — text embedding column, GTIN on listings, recommendations table

Revision ID: b7c4e8f2a931
Revises: 3f8a12c9e041
Create Date: 2026-08-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b7c4e8f2a931"
down_revision: Union[str, None] = "3f8a12c9e041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEXT_EMBEDDING_DIM = 768  # intfloat/multilingual-e5-base

recommendation_type_enum = sa.Enum(
    "genome_match", "oracle_pick", "prism_price", name="recommendation_type"
)
recommendation_status_enum = sa.Enum(
    "pending", "approved", "rejected", "edited", name="recommendation_status"
)


def upgrade() -> None:
    # --- listings: GTIN column for genome step 1 ---
    op.add_column("listings", sa.Column("gtin", sa.Text, nullable=True))

    # --- products: text embedding column + HNSW index for cosine search ---
    # op.add_column can't express the pgvector type; use raw DDL instead.
    op.execute(
        f"ALTER TABLE products ADD COLUMN text_embedding vector({TEXT_EMBEDDING_DIM})"
    )
    op.execute(
        """
        CREATE INDEX ix_products_text_embedding
        ON products
        USING hnsw (text_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # --- recommendations table (ledger infrastructure, written from day 1) ---
    op.create_table(
        "recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", recommendation_type_enum, nullable=False),
        sa.Column("shelf_slot_id", UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("listing_id", UUID(as_uuid=True), sa.ForeignKey("listings.id"), nullable=True),
        sa.Column("recommended_value", sa.Text, nullable=True),
        sa.Column("reasoning_text", sa.Text, nullable=False),
        sa.Column("evidence_json", sa.JSON, nullable=False),
        sa.Column("status", recommendation_status_enum, nullable=False),
        sa.Column("edited_value", sa.Text, nullable=True),
        sa.Column("reviewed_by", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_recommendations_listing_id", "recommendations", ["listing_id"])
    op.create_index("ix_recommendations_product_id", "recommendations", ["product_id"])
    op.create_index("ix_recommendations_status", "recommendations", ["status"])


def downgrade() -> None:
    op.drop_table("recommendations")
    recommendation_type_enum.drop(op.get_bind(), checkfirst=True)
    recommendation_status_enum.drop(op.get_bind(), checkfirst=True)

    op.execute("DROP INDEX IF EXISTS ix_products_text_embedding")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS text_embedding")

    op.drop_column("listings", "gtin")
