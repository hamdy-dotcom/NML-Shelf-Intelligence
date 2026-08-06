"""
Genome matching pipeline — steps 1 and 2.

Step 1 (GTIN): exact match on barcode. Handles a minority of listings;
most KSA Salla merchants don't tag GTINs reliably.

Step 2 (text embedding): cosine similarity search via pgvector against
canonical product text_embedding. Arabic titles are the primary case.

Ambiguous matches (below HIGH_CONFIDENCE but above REVIEW_THRESHOLD) are
written to recommendations as pending — not auto-applied.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from genome.embedder import TextEmbedder
from shared.config import settings
from shared.models.listing import Listing
from shared.models.product import Product
from shared.models.recommendation import Recommendation, RecommendationStatus, RecommendationType

logger = logging.getLogger(__name__)

HIGH_CONFIDENCE = settings.genome_high_confidence_threshold
REVIEW_THRESHOLD = settings.genome_review_threshold


@dataclass
class CandidateMatch:
    product_id: uuid.UUID
    similarity: float
    canonical_name_ar: str | None


@dataclass
class RunResult:
    total_unresolved: int
    matched: int = 0
    created: int = 0
    queued_for_review: int = 0
    match_details: list[dict] = field(default_factory=list)


def _search_by_embedding(
    db: Session, embedding: list[float], k: int = 5
) -> list[CandidateMatch]:
    """
    Cosine similarity search against canonical products that have an embedding.
    Uses pgvector <=> (cosine distance); similarity = 1 - distance.
    """
    emb_str = json.dumps(embedding)
    rows = db.execute(
        text(
            """
            SELECT id, canonical_name_ar,
                   1 - (text_embedding <=> CAST(:emb AS vector)) AS similarity
            FROM products
            WHERE text_embedding IS NOT NULL
            ORDER BY text_embedding <=> CAST(:emb AS vector)
            LIMIT :k
            """
        ),
        {"emb": emb_str, "k": k},
    ).fetchall()
    return [CandidateMatch(r.id, float(r.similarity), r.canonical_name_ar) for r in rows]


def _create_canonical(listing: Listing, embedding: list[float], db: Session) -> Product:
    product = Product(
        id=uuid.uuid4(),
        canonical_name_ar=listing.listing_title_raw,
        primary_image_url=listing.listing_image_url,
        text_embedding=embedding,
    )
    db.add(product)
    db.flush()  # visible to subsequent similarity searches within this pass
    return product


def _queue_for_review(
    listing: Listing, candidates: list[CandidateMatch], db: Session
) -> bool:
    """
    Insert a pending recommendation for human review.
    Returns True if a new row was inserted, False if one already existed
    (enforced by the DB-level partial unique index on (listing_id) WHERE status=’pending’).
    Using ON CONFLICT DO NOTHING rather than a SELECT-then-INSERT because two
    concurrent genome passes can both pass an app-level check before either commits.
    """
    best = candidates[0]
    evidence = {
        "listing_store": listing.store_name,
        "listing_title": listing.listing_title_raw,
        "listing_price_sar": str(listing.price),
        "top_candidates": [
            {
                "product_id": str(c.product_id),
                "similarity": round(c.similarity, 4),
                "canonical_name_ar": c.canonical_name_ar,
            }
            for c in candidates[:3]
        ],
    }
    reasoning = (
        f"Listing ‘{listing.listing_title_raw}’ from {listing.store_name} "
        f"matches canonical product ‘{best.canonical_name_ar}’ "
        f"with {round(best.similarity * 100, 1)}% text-embedding confidence. "
        f"Below auto-apply threshold ({HIGH_CONFIDENCE * 100:.0f}%) — manual review needed."
    )
    stmt = (
        pg_insert(Recommendation)
        .values(
            id=uuid.uuid4(),
            type=RecommendationType.genome_match,
            product_id=best.product_id,
            listing_id=listing.id,
            recommended_value=str(best.product_id),
            reasoning_text=reasoning,
            evidence_json=evidence,
            status=RecommendationStatus.pending,
            created_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_nothing(index_elements=None)  # relies on the partial unique index
    )
    r = db.execute(stmt)
    return r.rowcount > 0


def _try_gtin(listing: Listing, db: Session, result: RunResult) -> bool:
    """Step 1: GTIN exact match. Returns True and updates listing if resolved."""
    if not listing.gtin:
        return False
    product = db.query(Product).filter(Product.gtin == listing.gtin).first()
    if not product:
        return False
    listing.product_id = product.id
    listing.resolved_by = "genome:gtin"
    db.flush()
    result.matched += 1
    result.match_details.append(
        {
            "listing_id": str(listing.id),
            "listing_title": listing.listing_title_raw,
            "store_name": listing.store_name,
            "resolved_by": "genome:gtin",
            "matched_product_id": str(product.id),
            "similarity": 1.0,
        }
    )
    return True


def _try_text_embedding(
    listing: Listing, db: Session, embedder: TextEmbedder, result: RunResult
) -> None:
    """Step 2: cosine similarity search on text embeddings."""
    embedding = embedder.embed(listing.listing_title_raw)
    candidates = _search_by_embedding(db, embedding)

    if candidates and candidates[0].similarity >= HIGH_CONFIDENCE:
        best = candidates[0]
        listing.product_id = best.product_id
        listing.resolved_by = "genome:text_embedding"
        db.flush()
        result.matched += 1
        result.match_details.append(
            {
                "listing_id": str(listing.id),
                "listing_title": listing.listing_title_raw,
                "store_name": listing.store_name,
                "resolved_by": "genome:text_embedding",
                "matched_product_id": str(best.product_id),
                "canonical_name_ar": best.canonical_name_ar,
                "similarity": round(best.similarity, 4),
            }
        )
    elif candidates and candidates[0].similarity >= REVIEW_THRESHOLD:
        if _queue_for_review(listing, candidates, db):
            result.queued_for_review += 1
    else:
        # No confident match — seed a new canonical product from this listing
        new_product = _create_canonical(listing, embedding, db)
        listing.product_id = new_product.id
        listing.resolved_by = "genome:new_canonical"
        result.created += 1


def run_genome_pass(db: Session, embedder: TextEmbedder) -> RunResult:
    """
    One genome pass over every listing that has no product_id yet.
    Processes in scraped_at / id order so the first store seen seeds the
    canonical product and subsequent stores match against it.
    """
    unresolved = (
        db.query(Listing)
        .filter(Listing.product_id.is_(None))
        .order_by(Listing.scraped_at, Listing.id)
        .all()
    )
    result = RunResult(total_unresolved=len(unresolved))
    logger.info("Genome pass: %d unresolved listings", len(unresolved))

    for listing in unresolved:
        if _try_gtin(listing, db, result):
            continue
        _try_text_embedding(listing, db, embedder, result)

    db.commit()
    logger.info(
        "Genome pass complete — matched=%d created=%d queued=%d",
        result.matched,
        result.created,
        result.queued_for_review,
    )
    return result
