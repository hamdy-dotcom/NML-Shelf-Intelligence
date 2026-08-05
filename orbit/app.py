import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from orbit.jobs import pull_meta_ads_job, pull_salla_job, start_scheduler, stop_scheduler
from shared.config import settings
from shared.db import get_db

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.orbit_run_initial_pull:
        logger.info("Running initial data pull on startup")
        await asyncio.to_thread(pull_salla_job)
        await asyncio.to_thread(pull_meta_ads_job)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="NML Orbit", version="0.1.0", lifespan=lifespan)


@app.get("/orbit/health")
def health():
    return {
        "status": "ok",
        "service": "orbit",
        "mock_mode": settings.orbit_mock_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/orbit/freshness")
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


@app.post("/orbit/trigger/salla")
def trigger_salla():
    """Manually trigger a Salla API pull outside the schedule."""
    pull_salla_job()
    return {"status": "ok", "job": "salla_pull"}


@app.post("/orbit/trigger/ads/meta")
def trigger_meta_ads():
    """Manually trigger a Meta Ad Library pull outside the schedule."""
    pull_meta_ads_job()
    return {"status": "ok", "job": "meta_ads_pull"}
