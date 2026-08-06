from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from genome.embedder import get_embedder
from genome.matcher import run_genome_pass
from shared.db import get_db

router = APIRouter(prefix="/genome")


@router.get("/health")
def health():
    return {"status": "ok", "service": "genome"}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Resolution coverage — how many listings have been linked to a canonical product."""
    row = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(product_id) AS resolved,
                COUNT(*) - COUNT(product_id) AS unresolved
            FROM listings
            """
        )
    ).fetchone()
    by_step = db.execute(
        text(
            """
            SELECT resolved_by, COUNT(*) AS count
            FROM listings
            WHERE product_id IS NOT NULL
            GROUP BY resolved_by
            ORDER BY count DESC
            """
        )
    ).fetchall()
    product_count = db.execute(text("SELECT COUNT(*) FROM products")).scalar()
    pending_reviews = db.execute(
        text("SELECT COUNT(*) FROM recommendations WHERE status = 'pending'")
    ).scalar()
    return {
        "listings": {"total": row.total, "resolved": row.resolved, "unresolved": row.unresolved},
        "products": {"canonical_count": product_count},
        "pending_reviews": pending_reviews,
        "resolution_by_step": [{"step": r.resolved_by, "count": r.count} for r in by_step],
    }


@router.post("/run")
def run_genome(db: Session = Depends(get_db)):
    """
    Run one genome pass over all unresolved listings.
    Returns match details so cross-store matches are immediately visible.
    """
    embedder = get_embedder()
    result = run_genome_pass(db, embedder)
    return {
        "stats": {
            "total_unresolved": result.total_unresolved,
            "matched": result.matched,
            "created": result.created,
            "queued_for_review": result.queued_for_review,
        },
        "cross_store_matches": [m for m in result.match_details if m["resolved_by"] == "genome:text_embedding"],
        "gtin_matches": [m for m in result.match_details if m["resolved_by"] == "genome:gtin"],
    }
