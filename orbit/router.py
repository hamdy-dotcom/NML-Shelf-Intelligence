from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from orbit.jobs import pull_meta_ads_job, pull_salla_job
from shared.config import settings
from shared.db import get_db

router = APIRouter(prefix="/orbit")


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "orbit",
        "mock_mode": settings.orbit_mock_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/freshness")
def freshness(db: Session = Depends(get_db)):
    """Last scraped_at per listing source and last observed_at per ad platform."""
    listing_rows = db.execute(
        text(
            """
            SELECT source, MAX(scraped_at) AS last_scraped_at, COUNT(*) AS listing_count
            FROM listings
            GROUP BY source
            ORDER BY source
            """
        )
    ).fetchall()

    ad_rows = db.execute(
        text(
            """
            SELECT platform, MAX(observed_at) AS last_observed_at, COUNT(*) AS signal_count
            FROM ad_signals
            GROUP BY platform
            ORDER BY platform
            """
        )
    ).fetchall()

    return {
        "listings": [
            {
                "source": r.source,
                "last_scraped_at": r.last_scraped_at,
                "listing_count": r.listing_count,
            }
            for r in listing_rows
        ],
        "ad_signals": [
            {
                "platform": r.platform,
                "last_observed_at": r.last_observed_at,
                "signal_count": r.signal_count,
            }
            for r in ad_rows
        ],
    }


@router.post("/trigger/salla")
def trigger_salla():
    """Manually trigger a Salla API pull outside the schedule."""
    pull_salla_job()
    return {"status": "ok", "job": "salla_pull"}


@router.post("/trigger/ads/meta")
def trigger_meta_ads():
    """Manually trigger a Meta Ad Library pull outside the schedule."""
    pull_meta_ads_job()
    return {"status": "ok", "job": "meta_ads_pull"}
