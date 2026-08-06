"""
Ledger — human review queue for AI-generated recommendations.

Every genome match below the HIGH_CONFIDENCE threshold lands here before being
applied. Approve/reject/edit actions are logged with reviewer identity and
timestamp so the decision log can be used for genome/oracle/prism retraining.

Phase 1 covers genome_match items. oracle_pick and prism_price items will be
enqueued by those modules when they are built; the endpoints here already
handle them by type.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.db import get_db
from shared.models.listing import Listing
from shared.models.recommendation import Recommendation, RecommendationStatus

router = APIRouter(prefix="/ledger")

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ApproveBody(BaseModel):
    reviewed_by: str


class RejectBody(BaseModel):
    reviewed_by: str


class EditBody(BaseModel):
    reviewed_by: str
    edited_value: str  # genome_match: product_id UUID; prism_price: SAR string


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, rec_id: uuid.UUID) -> Recommendation:
    rec = db.get(Recommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


def _assert_pending(rec: Recommendation) -> None:
    if rec.status != RecommendationStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Recommendation already reviewed (status={rec.status.value})",
        )


def _enrich_rows(db: Session, rows: list[Any]) -> list[dict]:
    """
    Join listing and product context onto raw recommendation rows so reviewers
    have all the information they need without a second request.
    """
    if not rows:
        return []

    rec_ids = [str(r.id) for r in rows]
    id_list = ", ".join(f"'{i}'" for i in rec_ids)

    listing_map: dict[str, dict] = {}
    listing_rows = db.execute(
        text(
            f"""
            SELECT r.id AS rec_id,
                   l.store_name, l.listing_title_raw, l.price, l.currency,
                   l.listing_image_url, l.scraped_at
            FROM recommendations r
            JOIN listings l ON l.id = r.listing_id
            WHERE r.id IN ({id_list})
              AND r.listing_id IS NOT NULL
            """
        )
    ).fetchall()
    for lr in listing_rows:
        listing_map[str(lr.rec_id)] = {
            "store_name": lr.store_name,
            "listing_title_raw": lr.listing_title_raw,
            "price": float(lr.price) if lr.price is not None else None,
            "currency": lr.currency,
            "listing_image_url": lr.listing_image_url,
            "scraped_at": lr.scraped_at.isoformat() if lr.scraped_at else None,
        }

    product_map: dict[str, dict] = {}
    product_rows = db.execute(
        text(
            f"""
            SELECT r.id AS rec_id,
                   p.id AS product_id, p.canonical_name_ar, p.canonical_name_en,
                   p.gtin, p.primary_image_url
            FROM recommendations r
            JOIN products p ON p.id = r.product_id
            WHERE r.id IN ({id_list})
              AND r.product_id IS NOT NULL
            """
        )
    ).fetchall()
    for pr in product_rows:
        product_map[str(pr.rec_id)] = {
            "product_id": str(pr.product_id),
            "canonical_name_ar": pr.canonical_name_ar,
            "canonical_name_en": pr.canonical_name_en,
            "gtin": pr.gtin,
            "primary_image_url": pr.primary_image_url,
        }

    result = []
    for r in rows:
        rid = str(r.id)
        result.append(
            {
                "id": rid,
                "type": r.type,
                "status": r.status,
                "reasoning_text": r.reasoning_text,
                "evidence_json": r.evidence_json,
                "recommended_value": r.recommended_value,
                "edited_value": r.edited_value,
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "listing": listing_map.get(rid),
                "recommended_product": product_map.get(rid),
            }
        )
    return result


def _apply_genome_match(db: Session, rec: Recommendation, product_id_str: str) -> None:
    """
    Write the resolved product_id back onto the listing so the match is live,
    not just logged. Called on approve (uses recommended_value) and edit (uses
    edited_value, which may point to a different product).
    """
    if not rec.listing_id:
        return
    try:
        product_uuid = uuid.UUID(product_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid product_id: {product_id_str}")

    listing = db.get(Listing, rec.listing_id)
    if not listing:
        return
    listing.product_id = product_uuid
    listing.resolved_by = "ledger:approved"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/queue")
def list_queue(
    status: str = "pending",
    type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    List review queue items, enriched with listing and product context.

    status: pending | approved | rejected | edited | all
    type:   genome_match | oracle_pick | prism_price (omit for all types)
    """
    valid_statuses = {"pending", "approved", "rejected", "edited", "all"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(valid_statuses)}")

    filters = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if status != "all":
        filters.append("r.status = :status")
        params["status"] = status

    if type is not None:
        filters.append("r.type = :type")
        params["type"] = type

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    count_row = db.execute(
        text(f"SELECT COUNT(*) FROM recommendations r {where}"), params
    ).scalar()

    rows = db.execute(
        text(
            f"""
            SELECT r.id, r.type, r.status, r.reasoning_text, r.evidence_json,
                   r.recommended_value, r.edited_value, r.reviewed_by, r.reviewed_at,
                   r.created_at, r.listing_id, r.product_id
            FROM recommendations r
            {where}
            ORDER BY r.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).fetchall()

    return {
        "total": count_row,
        "limit": limit,
        "offset": offset,
        "items": _enrich_rows(db, rows),
    }


@router.get("/queue/{rec_id}")
def get_queue_item(rec_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Fetch a single recommendation by id, with full listing + product context."""
    rec = _get_or_404(db, rec_id)
    enriched = _enrich_rows(db, [rec])
    return enriched[0]


@router.post("/queue/{rec_id}/approve")
def approve(rec_id: uuid.UUID, body: ApproveBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Approve a pending recommendation.
    For genome_match: applies the match to the listing immediately.
    """
    rec = _get_or_404(db, rec_id)
    _assert_pending(rec)

    now = datetime.now(timezone.utc)
    rec.status = RecommendationStatus.approved
    rec.reviewed_by = body.reviewed_by
    rec.reviewed_at = now

    if rec.type.value == "genome_match" and rec.recommended_value:
        _apply_genome_match(db, rec, rec.recommended_value)

    db.commit()
    return {
        "id": str(rec.id),
        "status": rec.status.value,
        "reviewed_by": rec.reviewed_by,
        "reviewed_at": rec.reviewed_at.isoformat(),
    }


@router.post("/queue/{rec_id}/reject")
def reject(rec_id: uuid.UUID, body: RejectBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Reject a pending recommendation.
    The listing stays unresolved (product_id = NULL) for a future pass or manual fix.
    """
    rec = _get_or_404(db, rec_id)
    _assert_pending(rec)

    rec.status = RecommendationStatus.rejected
    rec.reviewed_by = body.reviewed_by
    rec.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "id": str(rec.id),
        "status": rec.status.value,
        "reviewed_by": rec.reviewed_by,
        "reviewed_at": rec.reviewed_at.isoformat(),
    }


@router.post("/queue/{rec_id}/edit")
def edit(rec_id: uuid.UUID, body: EditBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Edit a pending recommendation with a corrected value.
    For genome_match: edited_value must be a valid product_id UUID; the listing
    is updated to point to that product instead of the originally recommended one.
    """
    rec = _get_or_404(db, rec_id)
    _assert_pending(rec)

    now = datetime.now(timezone.utc)
    rec.status = RecommendationStatus.edited
    rec.edited_value = body.edited_value
    rec.reviewed_by = body.reviewed_by
    rec.reviewed_at = now

    if rec.type.value == "genome_match":
        _apply_genome_match(db, rec, body.edited_value)

    db.commit()
    return {
        "id": str(rec.id),
        "status": rec.status.value,
        "edited_value": rec.edited_value,
        "reviewed_by": rec.reviewed_by,
        "reviewed_at": rec.reviewed_at.isoformat(),
    }
