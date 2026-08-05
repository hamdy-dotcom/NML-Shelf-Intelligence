"""Initial orbit schema — Listing, AdSignal, Product tables + pgvector extension

Revision ID: 3f8a12c9e041
Revises:
Create Date: 2026-08-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "3f8a12c9e041"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

listing_source_enum = sa.Enum("salla_api", "public_listing", "manual", name="listing_source")
ad_platform_enum = sa.Enum("meta", "tiktok", "snap", "google", name="ad_platform")


def upgrade() -> None:
    # pgvector extension — genome will add vector columns in a later migration.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name_ar", sa.Text, nullable=True),
        sa.Column("canonical_name_en", sa.Text, nullable=True),
        sa.Column("category", sa.Text, nullable=True),
        sa.Column("subcategory", sa.Text, nullable=True),
        sa.Column("gtin", sa.Text, nullable=True),
        sa.Column("primary_image_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # op.create_table creates listing_source type automatically here — single owner.
    op.create_table(
        "listings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("store_name", sa.Text, nullable=False),
        sa.Column("store_url", sa.Text, nullable=True),
        sa.Column("external_id", sa.Text, nullable=True),
        sa.Column("listing_title_raw", sa.Text, nullable=False),
        sa.Column("listing_image_url", sa.Text, nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.Text, nullable=False, server_default="SAR"),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", listing_source_enum, nullable=False),
        sa.Column("resolved_by", sa.Text, nullable=True),
    )
    op.create_unique_constraint(
        "uq_listing_store_external", "listings", ["store_name", "external_id"]
    )
    op.create_index("ix_listings_product_id", "listings", ["product_id"])
    op.create_index("ix_listings_scraped_at", "listings", ["scraped_at"])

    # op.create_table creates ad_platform type automatically here — single owner.
    op.create_table(
        "ad_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column(
            "listing_id",
            UUID(as_uuid=True),
            sa.ForeignKey("listings.id"),
            nullable=True,
        ),
        sa.Column("platform", ad_platform_enum, nullable=False),
        sa.Column("ad_count_active", sa.Integer, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ad_signals_product_observed", "ad_signals", ["product_id", "observed_at"]
    )
    op.create_index("ix_ad_signals_listing_id", "ad_signals", ["listing_id"])


def downgrade() -> None:
    op.drop_table("ad_signals")
    op.drop_index("ix_listings_scraped_at", "listings")
    op.drop_index("ix_listings_product_id", "listings")
    op.drop_table("listings")
    op.drop_table("products")

    # Tables are gone; now safe to drop their types.
    listing_source_enum.drop(op.get_bind(), checkfirst=True)
    ad_platform_enum.drop(op.get_bind(), checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS vector")
