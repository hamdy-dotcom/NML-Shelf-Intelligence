"""Partial unique index: at most one pending recommendation per listing

Revision ID: d4e2f9c1a087
Revises: c1d3f7a9b205
Create Date: 2026-08-06

A DB-level guarantee replaces the application-level check-then-insert that is
vulnerable to concurrent genome passes: two passes can both see a listing as
unresolved, compute embeddings, and INSERT before either commits. The partial
index on (listing_id) WHERE status = 'pending' makes the second INSERT fail;
ON CONFLICT DO NOTHING in the INSERT path swallows it cleanly.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "d4e2f9c1a087"
down_revision: Union[str, None] = "c1d3f7a9b205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove any existing duplicates before adding the constraint.
    # Keep the earliest-created row per listing_id where status = 'pending'.
    op.execute(
        """
        DELETE FROM recommendations
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY listing_id
                           ORDER BY created_at
                       ) AS rn
                FROM recommendations
                WHERE status = 'pending'
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_recommendations_pending_listing
        ON recommendations (listing_id)
        WHERE status = 'pending'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_recommendations_pending_listing")
