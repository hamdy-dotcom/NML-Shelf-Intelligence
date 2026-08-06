"""
Sentinel — single-product deep dive.

Phase 1: text search only (Arabic/English product name via embedding similarity).
Image search and barcode lookup come in a later phase once genome image matching is built.

Search uses the same multilingual-e5-base embedder as genome, with the 'query: '
prefix so vectors are comparable to the 'passage: '-prefixed document embeddings
stored in products.text_embedding.
"""
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from genome.embedder import get_embedder
from shared.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sentinel")

# Calibrated empirically on fixture data (multilingual-e5-base, Arabic food products):
#   correct matches:  0.8213–0.8695 (Arabic exact queries)
#   noise floor:      ≤0.8255 (highest wrong result observed across all queries)
#
# SEARCH_FLOOR (0.83): confident matches — all noise eliminated, results are clean.
# BEST_GUESS_FLOOR (0.80): fallback when nothing clears SEARCH_FLOOR — return only the
#   single top result, flagged as a best guess. Chosen from diagnostic data: the two
#   short-query correct matches that fall below 0.83 (شامبو 0.8213, تمر 0.8287) both
#   clear 0.80 with margin; truly unrelated queries (e.g. "laptop" against Arabic food
#   products) score ~0.79 and are correctly suppressed.
SEARCH_FLOOR = 0.83
BEST_GUESS_FLOOR = 0.80


def _embed_query(q: str) -> str:
    """Return the query embedding as a JSON string for use with CAST(:emb AS vector)."""
    embedder = get_embedder()
    return json.dumps(embedder.embed_query(q))


def _product_listing_stats(db: Session, product_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """
    Batch-fetch listing count, distinct store count, and price range for a list of product ids.
    Returns a dict keyed by product_id.
    """
    if not product_ids:
        return {}

    id_list = ", ".join(f"'{pid}'" for pid in product_ids)
    rows = db.execute(
        text(
            f"""
            SELECT
                product_id,
                COUNT(*)                                               AS listing_count,
                COUNT(DISTINCT store_name)                             AS store_count,
                MIN(price)                                             AS price_min,
                MAX(price)                                             AS price_max,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)    AS price_median,
                MAX(currency)                                          AS currency
            FROM listings
            WHERE product_id IN ({id_list})
            GROUP BY product_id
            """
        )
    ).fetchall()

    return {
        r.product_id: {
            "listing_count": r.listing_count,
            "store_count": r.store_count,
            "price_min": float(r.price_min) if r.price_min is not None else None,
            "price_max": float(r.price_max) if r.price_max is not None else None,
            "price_median": float(r.price_median) if r.price_median is not None else None,
            "currency": r.currency,
        }
        for r in rows
    }


def _ad_signals_for_product(db: Session, product_id: uuid.UUID) -> dict:
    """
    Aggregate ad signal data for a product by joining AdSignal.search_term
    against listing titles for that product.  Ad signals are currently stored
    with search_term = the Arabic product name pulled from orbit's listing set,
    so this join captures the link until genome explicitly sets ad_signal.product_id.
    """
    row = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(a.ad_count_active), 0)   AS total_active,
                ARRAY_AGG(DISTINCT a.platform::text)   AS platforms
            FROM ad_signals a
            JOIN listings l ON l.listing_title_raw ILIKE '%' || a.search_term || '%'
            WHERE l.product_id = :product_id
            """
        ),
        {"product_id": str(product_id)},
    ).fetchone()

    return {
        "total_active": int(row.total_active) if row.total_active else 0,
        "platforms": [p for p in (row.platforms or []) if p],
    }


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Arabic or English product name"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Text search over canonical products using cosine similarity.
    Arabic is the primary case — the embedder handles it natively.
    Returns matched products with per-product listing counts and price ranges.
    """
    emb_str = _embed_query(q)

    # Fetch enough candidates to cover both the confident set and a potential best-guess
    # fallback in one round-trip. The fallback only ever surfaces the single top result,
    # so LIMIT limit+1 is sufficient.
    candidates = db.execute(
        text(
            """
            SELECT
                id,
                canonical_name_ar,
                canonical_name_en,
                category,
                gtin,
                primary_image_url,
                1 - (text_embedding <=> CAST(:emb AS vector)) AS similarity
            FROM products
            WHERE text_embedding IS NOT NULL
              AND 1 - (text_embedding <=> CAST(:emb AS vector)) >= :best_guess_floor
            ORDER BY text_embedding <=> CAST(:emb AS vector)
            LIMIT :limit
            """
        ),
        {"emb": emb_str, "best_guess_floor": BEST_GUESS_FLOOR, "limit": limit},
    ).fetchall()

    if not candidates:
        return {"query": q, "results": []}

    confident = [r for r in candidates if float(r.similarity) >= SEARCH_FLOOR]
    if confident:
        rows = confident
        is_best_guess = False
    else:
        # Nothing cleared the confident floor — surface only the top result, flagged.
        rows = candidates[:1]
        is_best_guess = True

    product_ids = [r.id for r in rows]
    stats = _product_listing_stats(db, product_ids)

    results = []
    for r in rows:
        s = stats.get(r.id, {})
        results.append(
            {
                "product_id": str(r.id),
                "canonical_name_ar": r.canonical_name_ar,
                "canonical_name_en": r.canonical_name_en,
                "category": r.category,
                "gtin": r.gtin,
                "primary_image_url": r.primary_image_url,
                "similarity": round(float(r.similarity), 4),
                "match_quality": "best_guess" if is_best_guess else "confident",
                "store_count": s.get("store_count", 0),
                "listing_count": s.get("listing_count", 0),
                "price_range": {
                    "min": s.get("price_min"),
                    "max": s.get("price_max"),
                    "median": s.get("price_median"),
                    "currency": s.get("currency", "SAR"),
                }
                if s.get("price_min") is not None
                else None,
                "resolved": s.get("listing_count", 0) > 0,
            }
        )

    return {"query": q, "results": results}


@router.get("/product/{product_id}")
def product_detail(product_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Full deep-dive for a resolved canonical product:
    - All matched listings across stores
    - Price range (min / max / median)
    - Active ad count and platforms
    """
    product_row = db.execute(
        text(
            """
            SELECT id, canonical_name_ar, canonical_name_en,
                   category, subcategory, gtin, primary_image_url,
                   created_at, updated_at
            FROM products
            WHERE id = :product_id
            """
        ),
        {"product_id": str(product_id)},
    ).fetchone()

    if not product_row:
        raise HTTPException(status_code=404, detail="Product not found")

    listing_rows = db.execute(
        text(
            """
            SELECT id, store_name, store_url, listing_title_raw,
                   listing_image_url, price, currency, scraped_at, resolved_by
            FROM listings
            WHERE product_id = :product_id
            ORDER BY scraped_at DESC
            """
        ),
        {"product_id": str(product_id)},
    ).fetchall()

    price_stats: dict[str, Any] = {}
    if listing_rows:
        ps = db.execute(
            text(
                """
                SELECT
                    MIN(price)                                             AS price_min,
                    MAX(price)                                             AS price_max,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)    AS price_median,
                    COUNT(DISTINCT store_name)                             AS store_count,
                    MAX(currency)                                          AS currency
                FROM listings
                WHERE product_id = :product_id
                  AND price IS NOT NULL
                """
            ),
            {"product_id": str(product_id)},
        ).fetchone()
        if ps and ps.price_min is not None:
            price_stats = {
                "min": float(ps.price_min),
                "max": float(ps.price_max),
                "median": float(ps.price_median),
                "store_count": ps.store_count,
                "currency": ps.currency,
            }

    ad_data = _ad_signals_for_product(db, product_id)

    return {
        "product": {
            "id": str(product_row.id),
            "canonical_name_ar": product_row.canonical_name_ar,
            "canonical_name_en": product_row.canonical_name_en,
            "category": product_row.category,
            "subcategory": product_row.subcategory,
            "gtin": product_row.gtin,
            "primary_image_url": product_row.primary_image_url,
            "created_at": product_row.created_at.isoformat() if product_row.created_at else None,
        },
        "listings": [
            {
                "id": str(r.id),
                "store_name": r.store_name,
                "store_url": r.store_url,
                "listing_title_raw": r.listing_title_raw,
                "listing_image_url": r.listing_image_url,
                "price": float(r.price) if r.price is not None else None,
                "currency": r.currency,
                "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
                "resolved_by": r.resolved_by,
            }
            for r in listing_rows
        ],
        "price_range": price_stats or None,
        "ad_signals": ad_data,
    }
