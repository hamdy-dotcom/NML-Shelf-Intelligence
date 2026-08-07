import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from orbit.jobs import (
    pull_meta_ads_job,
    pull_salla_job,
    scheduler,
    start_scheduler,
    stop_scheduler,
)
from orbit.router import router as orbit_router
from genome.router import router as genome_router
from sentinel.router import router as sentinel_router
from ledger.router import router as ledger_router
from atlas.router import router as atlas_router
from atlas.seeder import seed_atlas
from prism.router import router as prism_router
from pulse.router import router as pulse_router, take_snapshot as pulse_snapshot
from oracle.router import router as oracle_router
from shared.config import settings
from shared.db import SessionLocal

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _pulse_snapshot_job() -> None:
    """Scheduled wrapper — captures AdSignal state after each orbit ad pull."""
    db = SessionLocal()
    try:
        result = pulse_snapshot(db)
        logger.info("Pulse snapshot: captured %d signals at %s", result.signals_captured, result.snapshotted_at)
    except Exception:
        logger.exception("Pulse snapshot job failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.orbit_run_initial_pull:
        logger.info("Running initial data pull on startup")
        await asyncio.to_thread(pull_salla_job)
        await asyncio.to_thread(pull_meta_ads_job)
        # Snapshot right after startup pull so the first scheduled scan has data
        await asyncio.to_thread(_pulse_snapshot_job)
    await asyncio.to_thread(seed_atlas)
    start_scheduler()
    # Add pulse snapshot on the same interval as the ad pull — runs in lock-step
    scheduler.add_job(
        _pulse_snapshot_job,
        "interval",
        minutes=settings.orbit_ad_poll_interval_minutes,
        id="pulse_snapshot",
        replace_existing=True,
    )
    yield
    stop_scheduler()


app = FastAPI(title="NML Shelf Intelligence", version="0.1.0", lifespan=lifespan)

app.include_router(orbit_router)
app.include_router(genome_router)
app.include_router(sentinel_router)
app.include_router(ledger_router)
app.include_router(atlas_router)
app.include_router(prism_router)
app.include_router(pulse_router)
app.include_router(oracle_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nml-shelf-intelligence"}
