import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from shared.config import settings
from shared.db import get_db
from shared.models.recommendation import Recommendation, RecommendationStatus, RecommendationType
from shared.models.shelf_slot import ShelfSlot, SlotStatus
from shared.models.store import Store

from .scorer import score_slot

router = APIRouter(prefix="/oracle", tags=["oracle"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class CreateSlotRequest(BaseModel):
    store_id: uuid.UUID
    category: str
    open_date: datetime
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("category must not be empty")
        return v


class SlotOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    category: str
    open_date: datetime
    status: str
    filled_at: datetime | None
    filled_product_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


class ComponentScoreOut(BaseModel):
    raw_value: float | int | None
    normalized: float
    weight: float
    weighted: float
    note: str | None = None


class CandidateOut(BaseModel):
    rank: int
    product_id: uuid.UUID
    canonical_name_ar: str | None
    canonical_name_en: str | None
    category: str | None
    median_price: float | None
    currency: str
    listing_count: int
    ad_count: int
    total_score: float
    components: dict[str, ComponentScoreOut]
    reasoning_fragment: str


class RecommendResponse(BaseModel):
    recommendation_id: uuid.UUID
    slot_id: uuid.UUID
    store_id: uuid.UUID
    cluster_id: uuid.UUID | None
    cluster_label: str | None
    income_tier: str | None
    footfall_tier: str | None
    category_filter: str
    category_filter_matched: bool
    candidates_evaluated: int
    top_k_returned: int
    ranked: list[CandidateOut]
    reasoning_text: str
    weights_used: dict[str, float]
    data_quality_notes: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slot_to_out(slot: ShelfSlot) -> SlotOut:
    return SlotOut(
        id=slot.id,
        store_id=slot.store_id,
        category=slot.category,
        open_date=slot.open_date,
        status=slot.status.value,
        filled_at=slot.filled_at,
        filled_product_id=slot.filled_product_id,
        notes=slot.notes,
        created_at=slot.created_at,
    )


def _get_weights() -> dict[str, float]:
    return {
        "velocity":      settings.oracle_weight_velocity,
        "ad_intensity":  settings.oracle_weight_ad_intensity,
        "category_gap":  settings.oracle_weight_category_gap,
        "price_fit":     settings.oracle_weight_price_fit,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
def health():
    return {"status": "ok", "module": "oracle"}


@router.get("/weights")
def get_weights():
    """Return the active scoring weights and what each signal measures."""
    w = _get_weights()
    total = sum(w.values())
    return {
        "weights": w,
        "total": round(total, 4),
        "signals": {
            "velocity": {
                "description": "COUNT(resolved listings) per product — proxy for online demand. Real = YES (weak proxy; actual order volume would be stronger).",
                "real_data": "partial",
            },
            "ad_intensity": {
                "description": "Active ad count from AdSignal matching product listing titles. Real = YES (mock values in fixture, structure is real).",
                "real_data": "partial",
            },
            "category_gap": {
                "description": "Whether this category is under-represented in the target cluster. Real = NO — requires physical stocking data. Scored 0.50 neutral until integrated.",
                "real_data": "placeholder",
            },
            "price_fit": {
                "description": "How well the product's online median price fits the cluster's income tier. Real = YES (computed via prism cluster logic).",
                "real_data": "yes",
            },
        },
        "notes": (
            "Phase 1 weights are starting heuristics. "
            "Once ledger has approve/reject volume on oracle picks, retrain to Phase 2."
        ),
    }


@router.post("/slots", response_model=SlotOut, status_code=201)
def create_slot(body: CreateSlotRequest, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == body.store_id).first()
    if store is None:
        raise HTTPException(status_code=404, detail=f"Store {body.store_id} not found")

    slot = ShelfSlot(
        id=uuid.uuid4(),
        store_id=body.store_id,
        category=body.category,
        open_date=body.open_date,
        status=SlotStatus.open,
        notes=body.notes,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return _slot_to_out(slot)


@router.get("/slots", response_model=list[SlotOut])
def list_slots(
    store_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(ShelfSlot).order_by(ShelfSlot.created_at.desc())
    if store_id:
        q = q.filter(ShelfSlot.store_id == store_id)
    if status:
        try:
            q = q.filter(ShelfSlot.status == SlotStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status '{status}'. Use 'open' or 'filled'.")
    return [_slot_to_out(s) for s in q.limit(limit).all()]


@router.get("/slots/{slot_id}", response_model=SlotOut)
def get_slot(slot_id: uuid.UUID, db: Session = Depends(get_db)):
    slot = db.query(ShelfSlot).filter(ShelfSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
    return _slot_to_out(slot)


@router.post("/slots/{slot_id}/recommend", response_model=RecommendResponse)
def recommend(slot_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Run oracle scoring against an open slot and write the ranked result to ledger.

    Scoring is Phase 1 (weighted, no ML). The full candidate list with per-signal
    scores and data-quality notes is written to ledger.Recommendation so the team
    can inspect and approve/reject/edit before any pick is treated as final.

    Multiple calls produce multiple recommendation rows — each run is independent.
    The latest one is what the reviewer should act on.
    """
    slot = db.query(ShelfSlot).filter(ShelfSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
    if slot.status != SlotStatus.open:
        raise HTTPException(
            status_code=409,
            detail=f"Slot {slot_id} is already {slot.status.value} — cannot run oracle on a closed slot.",
        )

    weights = _get_weights()
    result = score_slot(
        slot_id=slot_id,
        store_id=slot.store_id,
        category=slot.category,
        weights=weights,
        top_k=settings.oracle_top_k,
        db=db,
    )

    # Write to ledger — the reviewer acts on this via /ledger/queue
    top_product_id = result.ranked[0].product_id if result.ranked else None
    rec = Recommendation(
        id=uuid.uuid4(),
        type=RecommendationType.oracle_pick,
        shelf_slot_id=slot_id,
        product_id=top_product_id,
        listing_id=None,
        recommended_value=str(top_product_id) if top_product_id else None,
        reasoning_text=result.reasoning_text,
        evidence_json=result.evidence,
        status=RecommendationStatus.pending,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return RecommendResponse(
        recommendation_id=rec.id,
        slot_id=slot_id,
        store_id=slot.store_id,
        cluster_id=result.cluster_id,
        cluster_label=result.cluster_label,
        income_tier=result.income_tier,
        footfall_tier=result.footfall_tier,
        category_filter=result.category_filter,
        category_filter_matched=result.category_filter_matched,
        candidates_evaluated=result.candidates_evaluated,
        top_k_returned=result.top_k_returned,
        ranked=[
            CandidateOut(
                rank=c.rank,
                product_id=c.product_id,
                canonical_name_ar=c.canonical_name_ar,
                canonical_name_en=c.canonical_name_en,
                category=c.category,
                median_price=c.median_price,
                currency=c.currency,
                listing_count=c.listing_count,
                ad_count=c.ad_count,
                total_score=c.total_score,
                components={
                    k: ComponentScoreOut(
                        raw_value=v.raw_value,
                        normalized=v.normalized,
                        weight=v.weight,
                        weighted=v.weighted,
                        note=v.note,
                    )
                    for k, v in c.components.items()
                },
                reasoning_fragment=c.reasoning_fragment,
            )
            for c in result.ranked
        ],
        reasoning_text=result.reasoning_text,
        weights_used=result.weights_used,
        data_quality_notes=result.data_quality_notes,
    )
