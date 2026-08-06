import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from orbit.jobs import pull_meta_ads_job, pull_salla_job, start_scheduler, stop_scheduler
from orbit.router import router as orbit_router
from genome.router import router as genome_router
from sentinel.router import router as sentinel_router
from ledger.router import router as ledger_router
from shared.config import settings

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


app = FastAPI(title="NML Shelf Intelligence", version="0.1.0", lifespan=lifespan)

app.include_router(orbit_router)
app.include_router(genome_router)
app.include_router(sentinel_router)
app.include_router(ledger_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nml-shelf-intelligence"}
