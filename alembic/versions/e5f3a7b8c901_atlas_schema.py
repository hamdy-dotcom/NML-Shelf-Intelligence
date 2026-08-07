"""Atlas — StoreCluster and Store tables

Revision ID: e5f3a7b8c901
Revises: d4e2f9c1a087
Create Date: 2026-08-06

store_clusters and stores tables. Seed data (mock Panda/Othaim branches) is
loaded separately by atlas/seeder.py at application startup, not here — keeping
schema changes and data seeding orthogonal.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e5f3a7b8c901"
down_revision: Union[str, None] = "d4e2f9c1a087"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

store_chain_enum = sa.Enum("panda", "othaim", name="store_chain")


def upgrade() -> None:
    op.create_table(
        "store_clusters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("income_tier", sa.Text, nullable=False),
        sa.Column("footfall_tier", sa.Text, nullable=False),
        sa.Column("region_code", sa.Text, nullable=False),
        sa.Column("region_name_ar", sa.Text, nullable=False),
        sa.Column("region_name_en", sa.Text, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("data_source", sa.Text, nullable=False, server_default="mock_fixture"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_table(
        "stores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name_ar", sa.Text, nullable=False),
        sa.Column("name_en", sa.Text, nullable=False),
        sa.Column("chain", store_chain_enum, nullable=False),
        sa.Column("branch_code", sa.Text, nullable=False, unique=True),
        sa.Column("city_ar", sa.Text, nullable=False),
        sa.Column("city_en", sa.Text, nullable=False),
        sa.Column("region_code", sa.Text, nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("lon", sa.Numeric(9, 6), nullable=True),
        sa.Column(
            "cluster_id",
            UUID(as_uuid=True),
            sa.ForeignKey("store_clusters.id"),
            nullable=True,
        ),
        sa.Column("cluster_override", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cluster_override_by", sa.Text, nullable=True),
        sa.Column("cluster_override_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_source", sa.Text, nullable=False, server_default="mock_fixture"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_stores_cluster_id", "stores", ["cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_stores_cluster_id", "stores")
    op.drop_table("stores")
    store_chain_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_table("store_clusters")
