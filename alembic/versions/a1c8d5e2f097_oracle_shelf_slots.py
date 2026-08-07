"""oracle shelf_slots table

Revision ID: a1c8d5e2f097
Revises: f6a4b2d8e713
Create Date: 2026-08-07

ShelfSlot represents a buyer's intent: a specific store + category combination
where a slot is open and oracle is asked to rank candidate products.
Oracle picks land in ledger.recommendations with type='oracle_pick'.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1c8d5e2f097"
down_revision = "f6a4b2d8e713"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE slot_status AS ENUM ('open', 'filled')")

    op.create_table(
        "shelf_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "store_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stores.id"),
            nullable=False,
        ),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("open_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("open", "filled", name="slot_status", create_type=False),
            nullable=False,
            server_default="open",
        ),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "filled_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_shelf_slots_store_id", "shelf_slots", ["store_id"])
    op.create_index("ix_shelf_slots_status", "shelf_slots", ["status"])


def downgrade() -> None:
    op.drop_index("ix_shelf_slots_status", table_name="shelf_slots")
    op.drop_index("ix_shelf_slots_store_id", table_name="shelf_slots")
    op.drop_table("shelf_slots")
    op.execute("DROP TYPE IF EXISTS slot_status")
