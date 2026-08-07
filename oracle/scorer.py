"""
Oracle Phase 1 scorer — weighted, fully inspectable, no ML.

Every number that goes into a score is returned in evidence_json so reviewers
can see exactly why a product ranked where it did. If a signal has no real data
behind it, it says so explicitly rather than silently returning a neutral value.

Signal inventory (honest as of current fixtures):
  velocity      — COUNT(listings WHERE product_id = X) across all Salla stores.
                  A weak proxy for demand; real order/GMV data would be better.
                  Multiple listings = multiple online sellers = some demand signal.
  ad_intensity  — SUM(ad_count_active) from AdSignal rows whose search_term
                  appears in any listing title for this product. Mock values in
                  fixture but structure is real; will improve as orbit accumulates.
  category_gap  — Placeholder. Requires physical stocking data for each cluster's
                  branches (what's on the shelf at each Panda/Othaim location). We
                  have none. Scored 0.50 (neutral) with an explicit data quality note.
  price_fit     — Real. Computed from the product's online median price vs. the
                  cluster's income tier target percentile. Uses prism's tier mapping.
"""
import math
from bisect import bisect_left
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Score component and result types
# ---------------------------------------------------------------------------

@dataclass
class ComponentScore:
    raw_value: float | int | None
    normalized: float          # 0.0–1.0
    weight: float
    weighted: float            # normalized * weight
    note: str | None = None    # set when data is absent or a proxy is used


@dataclass
class CandidateScore:
    product_id: UUID
    canonical_name_ar: str | None
    canonical_name_en: str | None
    category: str | None
    median_price: float | None
    currency: str
    listing_count: int
    ad_count: int
    total_score: float
    rank: int
    components: dict[str, ComponentScore]
    reasoning_fragment: str    # one-sentence plain-language summary for this candidate


@dataclass
class OracleResult:
    slot_id: UUID
    store_id: UUID
    cluster_id: UUID | None
    cluster_label: str | None
    income_tier: str | None
    footfall_tier: str | None
    category_filter: str
    category_filter_matched: bool   # False = fell back to all resolved products
    candidates_evaluated: int
    top_k_returned: int
    ranked: list[CandidateScore]
    reasoning_text: str
    evidence: dict
    weights_used: dict[str, float]
    data_quality_notes: list[str]


# ---------------------------------------------------------------------------
# Price-fit helpers (mirrors prism's tier logic without importing it)
# ---------------------------------------------------------------------------

# For each income tier, what price-rank percentile does this cluster prefer?
# high → prefers items in the top quartile of the candidate price range
# mid  → neutral (median)
# low  → prefers items in the bottom quartile
_PRICE_TARGET_PERCENTILE: dict[str, float] = {
    "high": 0.75,
    "mid":  0.50,
    "low":  0.25,
}


def _price_fit_score(
    product_price: float | None,
    all_prices: list[float],
    income_tier: str | None,
) -> tuple[float, str | None]:
    """
    Returns (normalized_score, note).
    Score = 1 - |product_price_rank - cluster_target_percentile|
    Neutral (0.5) with a note if price or cluster info is unavailable.
    """
    if product_price is None:
        return 0.5, "no price data for this product"
    if not all_prices:
        return 0.5, "no price data across candidates"
    tier = income_tier or "mid"
    target = _PRICE_TARGET_PERCENTILE.get(tier, 0.5)

    sorted_prices = sorted(all_prices)
    n = len(sorted_prices)
    rank = bisect_left(sorted_prices, product_price) / max(n - 1, 1)
    score = 1.0 - abs(rank - target)
    return round(score, 4), None


# ---------------------------------------------------------------------------
# DB queries (kept thin — logic stays in scorer, SQL just fetches)
# ---------------------------------------------------------------------------

def _fetch_resolved_products(category: str | None, db: Session) -> list[dict]:
    """
    Returns genome-resolved products (those with at least one listing via product_id).
    Filters by category if provided AND if any products with that category exist.
    Falls back to all resolved products otherwise.
    """
    base_sql = """
        SELECT DISTINCT ON (p.id)
            p.id,
            p.canonical_name_ar,
            p.canonical_name_en,
            p.category,
            p.gtin
        FROM products p
        WHERE EXISTS (
            SELECT 1 FROM listings l WHERE l.product_id = p.id
        )
    """

    if category:
        rows = db.execute(
            text(base_sql + " AND p.category ILIKE :cat"),
            {"cat": f"%{category}%"},
        ).fetchall()
        if rows:
            return [dict(r._mapping) for r in rows], True

    # Fall back to all resolved products
    rows = db.execute(text(base_sql)).fetchall()
    return [dict(r._mapping) for r in rows], False


def _fetch_listing_stats(product_id: UUID, db: Session) -> tuple[int, float | None, str]:
    """Returns (listing_count, median_price, currency)."""
    row = db.execute(
        text("""
            SELECT
                COUNT(*) AS listing_count,
                CAST(
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS NUMERIC(12,2)
                ) AS median_price,
                MAX(currency) AS currency
            FROM listings
            WHERE product_id = :pid AND price IS NOT NULL
        """),
        {"pid": str(product_id)},
    ).fetchone()
    if row is None:
        return 0, None, "SAR"
    return (
        int(row.listing_count),
        float(row.median_price) if row.median_price else None,
        row.currency or "SAR",
    )


def _fetch_ad_count(product_id: UUID, db: Session) -> int:
    """
    Total active ad count across all AdSignal terms that match any listing title
    for this product. Uses ILIKE containment: search_term appears in listing_title_raw.
    """
    row = db.execute(
        text("""
            SELECT COALESCE(SUM(a.ad_count_active), 0) AS total_ads
            FROM ad_signals a
            WHERE EXISTS (
                SELECT 1
                FROM listings l
                WHERE l.product_id = :pid
                  AND l.listing_title_raw ILIKE '%' || a.search_term || '%'
            )
        """),
        {"pid": str(product_id)},
    ).fetchone()
    return int(row.total_ads) if row else 0


def _fetch_store_cluster(store_id: UUID, db: Session) -> dict | None:
    """Returns cluster row for this store, or None if no cluster assigned."""
    row = db.execute(
        text("""
            SELECT
                sc.id        AS cluster_id,
                sc.label     AS cluster_label,
                sc.income_tier,
                sc.footfall_tier
            FROM stores s
            JOIN store_clusters sc ON sc.id = s.cluster_id
            WHERE s.id = :store_id
        """),
        {"store_id": str(store_id)},
    ).fetchone()
    return dict(row._mapping) if row else None


# ---------------------------------------------------------------------------
# Min-max normalisation helpers
# ---------------------------------------------------------------------------

def _normalize(values: list[float]) -> list[float]:
    mn, mx = min(values), max(values)
    if mx == mn:
        return [0.5] * len(values)   # flat — no discriminating signal
    return [(v - mn) / (mx - mn) for v in values]


# ---------------------------------------------------------------------------
# Plain-language fragment per candidate
# ---------------------------------------------------------------------------

def _reason_fragment(c: CandidateScore, income_tier: str | None) -> str:
    parts = []

    v = c.components["velocity"]
    if v.raw_value == 0:
        parts.append("no resolved online listings (new-to-market)")
    elif c.listing_count == 1:
        parts.append("listed on 1 online store")
    else:
        parts.append(f"listed across {c.listing_count} online stores")

    a = c.components["ad_intensity"]
    if a.raw_value == 0:
        parts.append("no active ad signals")
    else:
        parts.append(f"{c.ad_count} active ads on Meta")

    p = c.components["price_fit"]
    if c.median_price is not None:
        tier_word = {"high": "premium-tier", "mid": "mid-tier", "low": "budget-tier"}.get(
            income_tier or "mid", "cluster"
        )
        fit_word = "good fit" if p.normalized >= 0.65 else ("neutral" if p.normalized >= 0.40 else "poor fit")
        parts.append(f"price SAR {c.median_price:.2f} is a {fit_word} for {tier_word} cluster")

    gap = c.components["category_gap"]
    if gap.note:
        parts.append("category gap unknown (no stocking data)")

    return "; ".join(parts) + f" → score {c.total_score:.3f}"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def score_slot(
    slot_id: UUID,
    store_id: UUID,
    category: str,
    weights: dict[str, float],
    top_k: int,
    db: Session,
) -> OracleResult:
    data_quality_notes: list[str] = []

    # 1. Cluster context
    cluster = _fetch_store_cluster(store_id, db)
    if cluster is None:
        data_quality_notes.append(
            "Store has no cluster assigned — price_fit and category_gap scored neutral. "
            "Use PATCH /atlas/stores/{id}/cluster to assign one."
        )

    income_tier = cluster["income_tier"] if cluster else None
    footfall_tier = cluster["footfall_tier"] if cluster else None

    # 2. Candidate products
    product_rows, category_matched = _fetch_resolved_products(category, db)
    if not category_matched:
        data_quality_notes.append(
            f"No products with category matching '{category}' found — "
            "fell back to all genome-resolved products. Product categories are NULL "
            "until real product catalog data is loaded with categories set."
        )

    if not product_rows:
        return OracleResult(
            slot_id=slot_id,
            store_id=store_id,
            cluster_id=UUID(str(cluster["cluster_id"])) if cluster else None,
            cluster_label=cluster["cluster_label"] if cluster else None,
            income_tier=income_tier,
            footfall_tier=footfall_tier,
            category_filter=category,
            category_filter_matched=category_matched,
            candidates_evaluated=0,
            top_k_returned=0,
            ranked=[],
            reasoning_text=(
                f"No genome-resolved products found for category '{category}'. "
                "Run genome first to resolve listings to products."
            ),
            evidence={"error": "no_candidates"},
            weights_used=weights,
            data_quality_notes=data_quality_notes,
        )

    # 3. Gather raw signals per candidate
    raw: list[dict] = []
    for pr in product_rows:
        pid = UUID(str(pr["id"]))
        listing_count, median_price, currency = _fetch_listing_stats(pid, db)
        ad_count = _fetch_ad_count(pid, db)
        raw.append({
            "product_id": pid,
            "canonical_name_ar": pr["canonical_name_ar"],
            "canonical_name_en": pr["canonical_name_en"],
            "category": pr["category"],
            "listing_count": listing_count,
            "median_price": median_price,
            "currency": currency,
            "ad_count": ad_count,
        })

    # 4. Normalise each signal across all candidates
    listing_counts = [r["listing_count"] for r in raw]
    ad_counts = [r["ad_count"] for r in raw]
    prices_available = [r["median_price"] for r in raw if r["median_price"] is not None]

    norm_listings = _normalize([float(x) for x in listing_counts])
    norm_ads = _normalize([float(x) for x in ad_counts])

    # Category gap: full placeholder — no physical stocking data available
    gap_note = (
        "Placeholder — physical stocking data for cluster branches not yet available. "
        "This signal will be real once store planogram / POS data is integrated."
    )
    data_quality_notes.append(f"category_gap signal: {gap_note}")

    if not prices_available:
        data_quality_notes.append(
            "price_fit signal: no candidates have price data — all scored neutral."
        )

    # 5. Compute weighted total score per candidate
    candidates: list[CandidateScore] = []
    for i, r in enumerate(raw):
        v_norm = norm_listings[i]
        a_norm = norm_ads[i]
        gap_norm = 0.5          # explicit placeholder
        p_norm, p_note = _price_fit_score(r["median_price"], prices_available, income_tier)

        total = (
            weights["velocity"] * v_norm
            + weights["ad_intensity"] * a_norm
            + weights["category_gap"] * gap_norm
            + weights["price_fit"] * p_norm
        )
        total = round(total, 4)

        components = {
            "velocity": ComponentScore(
                raw_value=r["listing_count"],
                normalized=round(v_norm, 4),
                weight=weights["velocity"],
                weighted=round(weights["velocity"] * v_norm, 4),
                note="listing count across Salla stores — proxy for demand, not actual order volume",
            ),
            "ad_intensity": ComponentScore(
                raw_value=r["ad_count"],
                normalized=round(a_norm, 4),
                weight=weights["ad_intensity"],
                weighted=round(weights["ad_intensity"] * a_norm, 4),
            ),
            "category_gap": ComponentScore(
                raw_value=None,
                normalized=gap_norm,
                weight=weights["category_gap"],
                weighted=round(weights["category_gap"] * gap_norm, 4),
                note=gap_note,
            ),
            "price_fit": ComponentScore(
                raw_value=r["median_price"],
                normalized=round(p_norm, 4),
                weight=weights["price_fit"],
                weighted=round(weights["price_fit"] * p_norm, 4),
                note=p_note,
            ),
        }

        cand = CandidateScore(
            product_id=r["product_id"],
            canonical_name_ar=r["canonical_name_ar"],
            canonical_name_en=r["canonical_name_en"],
            category=r["category"],
            median_price=r["median_price"],
            currency=r["currency"],
            listing_count=r["listing_count"],
            ad_count=r["ad_count"],
            total_score=total,
            rank=0,          # assigned after sort
            components=components,
            reasoning_fragment="",   # assigned after sort
        )
        candidates.append(cand)

    # 6. Sort, assign ranks and reasoning fragments
    candidates.sort(key=lambda c: c.total_score, reverse=True)
    for i, c in enumerate(candidates):
        c.rank = i + 1
        c.reasoning_fragment = _reason_fragment(c, income_tier)

    top = candidates[:top_k]
    top_candidate = top[0] if top else None

    # 7. Build plain-language reasoning for the ledger entry
    cluster_desc = (
        f"'{cluster['cluster_label']}' cluster (income={income_tier}, footfall={footfall_tier})"
        if cluster else "no cluster assigned"
    )
    cat_note = (
        f"category filter '{category}' matched"
        if category_matched
        else f"no category match for '{category}' — ranked all {len(product_rows)} resolved products"
    )
    if top_candidate:
        winner = top_candidate
        reasoning_text = (
            f"Oracle ranked {len(candidates)} candidate product(s) for the '{category}' slot "
            f"at store {store_id} ({cluster_desc}). {cat_note}. "
            f"Top pick: {winner.canonical_name_ar or winner.canonical_name_en or str(winner.product_id)} "
            f"(rank 1/{len(candidates)}, score {winner.total_score:.3f}): "
            f"{winner.reasoning_fragment}. "
            f"Weights used — velocity: {weights['velocity']}, "
            f"ad_intensity: {weights['ad_intensity']}, "
            f"category_gap: {weights['category_gap']} (placeholder), "
            f"price_fit: {weights['price_fit']}."
        )
    else:
        reasoning_text = f"No scoreable candidates found for '{category}' slot."

    # 8. Build evidence dict (full ranked list for the ledger record)
    evidence = {
        "slot_id": str(slot_id),
        "store_id": str(store_id),
        "cluster_id": str(cluster["cluster_id"]) if cluster else None,
        "cluster_label": cluster["cluster_label"] if cluster else None,
        "income_tier": income_tier,
        "footfall_tier": footfall_tier,
        "category_filter": category,
        "category_filter_matched": category_matched,
        "candidates_evaluated": len(candidates),
        "weights": weights,
        "data_quality_notes": data_quality_notes,
        "ranked_candidates": [
            {
                "rank": c.rank,
                "product_id": str(c.product_id),
                "canonical_name_ar": c.canonical_name_ar,
                "canonical_name_en": c.canonical_name_en,
                "category": c.category,
                "median_price": c.median_price,
                "currency": c.currency,
                "total_score": c.total_score,
                "components": {
                    k: {
                        "raw_value": v.raw_value,
                        "normalized": v.normalized,
                        "weight": v.weight,
                        "weighted": v.weighted,
                        **({"note": v.note} if v.note else {}),
                    }
                    for k, v in c.components.items()
                },
                "reasoning_fragment": c.reasoning_fragment,
            }
            for c in top
        ],
    }

    return OracleResult(
        slot_id=slot_id,
        store_id=store_id,
        cluster_id=UUID(str(cluster["cluster_id"])) if cluster else None,
        cluster_label=cluster["cluster_label"] if cluster else None,
        income_tier=income_tier,
        footfall_tier=footfall_tier,
        category_filter=category,
        category_filter_matched=category_matched,
        candidates_evaluated=len(candidates),
        top_k_returned=len(top),
        ranked=top,
        reasoning_text=reasoning_text,
        evidence=evidence,
        weights_used=weights,
        data_quality_notes=data_quality_notes,
    )
