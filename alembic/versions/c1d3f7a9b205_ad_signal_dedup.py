"""AdSignal dedup — search_term column + unique constraint (platform, search_term)

Revision ID: c1d3f7a9b205
Revises: b7c4e8f2a931
Create Date: 2026-08-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d3f7a9b205"
down_revision: Union[str, None] = "b7c4e8f2a931"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ad_signals", sa.Column("search_term", sa.Text, nullable=False, server_default=""))
    # Remove the temporary server_default now that the column exists
    op.alter_column("ad_signals", "search_term", server_default=None)
    op.create_unique_constraint("uq_ad_signal_platform_term", "ad_signals", ["platform", "search_term"])


def downgrade() -> None:
    op.drop_constraint("uq_ad_signal_platform_term", "ad_signals", type_="unique")
    op.drop_column("ad_signals", "search_term")
