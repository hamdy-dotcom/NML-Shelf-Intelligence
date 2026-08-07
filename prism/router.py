import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.db import get_db
from shared.models.recommendation import Recommendation, RecommendationStatus, RecommendationType
from shared.models.store import Store, StoreCluster

from .pricing import CATEGORY_ELASTICITY, TIER_ADJUSTMENTS, compute_price

router = APIRouter(prefix="/prism", tags=["prism"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    product_id: uuid.UUID
    store_id: uuid.UUID


class RecommendResponse(BaseModel):
    recommendation_id: uuid.UUID
    product_id: uuid.UUID
    product_name_ar: str | None
    store_id: uuid.UUID
    store_name_ar: str
    store_branch_code: str
    cluster_id: uuid.UUID
    cluster_label: str
    income_tier: str
    footfall_tier: str
    base_price: str
    currency: str
    listing_count: int
    tier_base_adjustment: float
    elasticity_multiplier: float
    cluster_adjustment: float
    recommended_price: str
    reasoning_text: str
    evidence: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_median_price(product_id: uuid.UUID, db: Session) -> tuple[Decimal, Decimal, Decimal, int, str]:
    """Returns (median, min, max, count, currency) for resolved listings with prices."""
    row = db.execute(
        text("""
            SELECT
                CAST(
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS NUMERIC(12,2)
                ) AS median_price,
                MIN(price)   AS min_price,
                MAX(price)   AS max_price,
                COUNT(*)     AS listing_count,
                MAX(currency) AS currency
            FROM listings
            WHERE product_id = :product_id
              AND price IS NOT NULL
        """),
        {"product_id": str(product_id)},
    ).fetchone()

    if row is None or row.listing_count == 0 or row.median_price is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No priced listings found for product {product_id}. "
                "Run orbit + genome to ingest listings and resolve product matches first."
            ),
        )

    return (
        Decimal(str(row.median_price)),
        Decimal(str(row.min_price)),
        Decimal(str(row.max_price)),
        int(row.listing_count),
        row.currency or "SAR",
    )


def _get_product_name_and_category(product_id: uuid.UUID, db: Session) -> tuple[str | None, str | None]:
    row = db.execute(
        text("SELECT canonical_name_ar, category FROM products WHERE id = :id"),
        {"id": str(product_id)},
    ).fetchone()
    if row is None:
        return None, None
    return row.canonical_name_ar, row.category


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
def health():
    return {"status": "ok", "module": "prism"}


@router.get("/adjustments")
def get_adjustments():
    """Return the full pricing adjustment tables — inspect without reading source."""
    return {
        "tier_adjustments": TIER_ADJUSTMENTS,
        "category_elasticity": CATEGORY_ELASTICITY,
        "formula": "recommended_price = base_price * (1 + tier_adjustment * category_elasticity)",
        "notes": (
            "tier_adjustments and category_elasticity are starting heuristics, "
            "not empirically calibrated values. "
            "Replace when real ledger approve/reject volume becomes available."
        ),
    }


@router.post("/recommend", response_model=RecommendResponse)
def recommend(body: RecommendRequest, db: Session = Depends(get_db)):
    # 1. Resolve store → cluster
    store = db.query(Store).filter(Store.id == body.store_id).first()
    if store is None:
        raise HTTPException(status_code=404, detail=f"Store {body.store_id} not found")

    if store.cluster_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Store {body.store_id} has no cluster assigned. "
                "Use PATCH /atlas/stores/{id}/cluster to assign one."
            ),
        )

    cluster = db.query(StoreCluster).filter(StoreCluster.id == store.cluster_id).first()
    if cluster is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster {store.cluster_id} not found (data integrity issue)",
        )

    # 2. Fetch product
    product_name_ar, category = _get_product_name_and_category(body.product_id, db)
    if product_name_ar is None and category is None:
        # product not found at all
        row = db.execute(
            text("SELECT id FROM products WHERE id = :id"),
            {"id": str(body.product_id)},
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Product {body.product_id} not found")

    # 3. Fetch price range from genome-resolved listings
    median_price, min_price, max_price, listing_count, currency = _get_median_price(
        body.product_id, db
    )

    # 4. Compute recommended price
    result = compute_price(
        base_price=median_price,
        income_tier=cluster.income_tier,
        footfall_tier=cluster.footfall_tier,
        category=category,
        cluster_label=cluster.label,
        listing_count=listing_count,
        currency=currency,
    )

    # Extend evidence with price range context
    result.evidence["min_price"] = str(min_price)
    result.evidence["max_price"] = str(max_price)
    result.evidence["store_id"] = str(body.store_id)
    result.evidence["store_name_ar"] = store.name_ar
    result.evidence["cluster_id"] = str(cluster.id)

    # 5. Write to ledger
    rec = Recommendation(
        id=uuid.uuid4(),
        type=RecommendationType.prism_price,
        product_id=body.product_id,
        listing_id=None,
        shelf_slot_id=None,
        recommended_value=str(result.recommended_price),
        reasoning_text=result.reasoning_text,
        evidence_json=result.evidence,
        status=RecommendationStatus.pending,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return RecommendResponse(
        recommendation_id=rec.id,
        product_id=body.product_id,
        product_name_ar=product_name_ar,
        store_id=body.store_id,
        store_name_ar=store.name_ar,
        store_branch_code=store.branch_code,
        cluster_id=cluster.id,
        cluster_label=cluster.label,
        income_tier=cluster.income_tier,
        footfall_tier=cluster.footfall_tier,
        base_price=str(median_price),
        currency=currency,
        listing_count=listing_count,
        tier_base_adjustment=result.tier_base_adjustment,
        elasticity_multiplier=result.elasticity_multiplier,
        cluster_adjustment=result.cluster_adjustment,
        recommended_price=str(result.recommended_price),
        reasoning_text=result.reasoning_text,
        evidence=result.evidence,
    )
