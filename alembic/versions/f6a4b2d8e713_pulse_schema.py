"""pulse schema — ad snapshots and alerts

Revision ID: f6a4b2d8e713
Revises: e5f3a7b8c901
Create Date: 2026-08-07

PulseAdSnapshot: append-only time-series of AdSignal readings; written by
POST /pulse/snapshot after each orbit ad pull. This is the historical record
that spike detection compares against — AdSignal itself only stores the latest
reading per (platform, search_term).

PulseAlert: every alert emitted by pulse, acknowledged or not. Kept forever
for threshold tuning and eventual oracle feedback.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6a4b2d8e713"
down_revision = "e5f3a7b8c901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pulse_ad_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("search_term", sa.Text(), nullable=False),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("ad_count_active", sa.Integer(), nullable=False),
        sa.Column(
            "snapshotted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pulse_snapshots_term_at", "pulse_ad_snapshots", ["search_term", "snapshotted_at"]
    )
    op.create_index(
        "ix_pulse_snapshots_product_at", "pulse_ad_snapshots", ["product_id", "snapshotted_at"]
    )

    op.create_table(
        "pulse_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_type", sa.Text(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("search_term", sa.Text(), nullable=False),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("baseline_count", sa.Integer(), nullable=False),
        sa.Column("current_count", sa.Integer(), nullable=False),
        sa.Column("spike_ratio", sa.Numeric(8, 4), nullable=False),
        sa.Column("threshold_ratio", sa.Numeric(8, 4), nullable=False),
        sa.Column("sentinel_url", sa.Text(), nullable=False),
        sa.Column("evidence_json", postgresql.JSON(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_pulse_alerts_product_id", "pulse_alerts", ["product_id"])
    op.create_index("ix_pulse_alerts_created_at", "pulse_alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pulse_alerts_created_at", table_name="pulse_alerts")
    op.drop_index("ix_pulse_alerts_product_id", table_name="pulse_alerts")
    op.drop_table("pulse_alerts")

    op.drop_index("ix_pulse_snapshots_product_at", table_name="pulse_ad_snapshots")
    op.drop_index("ix_pulse_snapshots_term_at", table_name="pulse_ad_snapshots")
    op.drop_table("pulse_ad_snapshots")
