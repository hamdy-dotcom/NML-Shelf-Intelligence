import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from orbit.meta_client import MetaAdLibraryClient
from orbit.salla_client import RawListing, get_salla_clients
from shared.config import settings
from shared.db import SessionLocal
from shared.models.ad_signal import AdPlatform, AdSignal
from shared.models.listing import Listing, ListingSource

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _upsert_listing(db: Session, raw: RawListing, now: datetime) -> None:
    stmt = (
        pg_insert(Listing)
        .values(
            id=uuid.uuid4(),
            store_name=raw.store_name,
            store_url=raw.store_url,
            external_id=raw.external_id,
            listing_title_raw=raw.listing_title_raw,
            listing_image_url=raw.listing_image_url,
            price=raw.price,
            currency=raw.currency,
            scraped_at=now,
            source=ListingSource.salla_api,
            product_id=None,
            resolved_by=None,
        )
        .on_conflict_do_update(
            constraint="uq_listing_store_external",
            set_={
                "listing_title_raw": raw.listing_title_raw,
                "listing_image_url": raw.listing_image_url,
                "price": raw.price,
                "currency": raw.currency,
                "scraped_at": now,
                "store_url": raw.store_url,
            },
        )
    )
    db.execute(stmt)


def pull_salla_job() -> None:
    clients = get_salla_clients()
    now = datetime.now(timezone.utc)
    for client in clients:
        db = SessionLocal()
        try:
            listings = client.fetch_listings()
            for raw in listings:
                _upsert_listing(db, raw, now)
            db.commit()
            logger.info(
                "Upserted %d listings from Salla store '%s'", len(listings), client.store_name
            )
        except Exception:
            logger.exception("Failed to pull from Salla store '%s'", client.store_name)
            db.rollback()
        finally:
            db.close()


def _get_tracked_search_terms(db: Session) -> list[str]:
    rows = db.execute(
        text("SELECT DISTINCT listing_title_raw FROM listings LIMIT 200")
    ).fetchall()
    return [r.listing_title_raw for r in rows]


def pull_meta_ads_job() -> None:
    client = MetaAdLibraryClient(
        access_token=settings.meta_ad_library_access_token,
        mock_mode=settings.orbit_mock_mode,
    )
    db = SessionLocal()
    try:
        search_terms = [] if settings.orbit_mock_mode else _get_tracked_search_terms(db)
        try:
            signals = client.fetch_ad_signals(search_terms)
        except NotImplementedError:
            logger.info("Meta Ad Library not yet implemented — skipping")
            return

        now = datetime.now(timezone.utc)
        for sig in signals:
            db.add(
                AdSignal(
                    id=uuid.uuid4(),
                    platform=AdPlatform.meta,
                    ad_count_active=sig.ad_count_active,
                    observed_at=now,
                    product_id=None,
                    listing_id=None,
                )
            )
        db.commit()
        logger.info("Stored %d Meta ad signals", len(signals))
    except Exception:
        logger.exception("Failed to pull Meta ad signals")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        pull_salla_job,
        "interval",
        minutes=settings.orbit_salla_poll_interval_minutes,
        id="salla_pull",
        replace_existing=True,
    )
    scheduler.add_job(
        pull_meta_ads_job,
        "interval",
        minutes=settings.orbit_ad_poll_interval_minutes,
        id="meta_ads_pull",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Orbit scheduler started — Salla every %dm, ads every %dm",
        settings.orbit_salla_poll_interval_minutes,
        settings.orbit_ad_poll_interval_minutes,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Orbit scheduler stopped")
