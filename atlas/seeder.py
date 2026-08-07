"""
Atlas seed — loads mock Store/StoreCluster data on startup when atlas_mock_mode=True.

Idempotent: if any store rows already exist, skips entirely. Safe to call on
every startup. When real GASTAT data replaces the fixture, set atlas_mock_mode=False
in .env and run a proper data-import command instead.
"""
import json
import logging
import uuid
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.config import settings
from shared.db import SessionLocal
from shared.models.store import Store, StoreChain, StoreCluster

logger = logging.getLogger(__name__)

_FIXTURE = Path(__file__).parent / "fixtures" / "sample_stores.json"


def seed_atlas() -> None:
    if not settings.atlas_mock_mode:
        return

    db = SessionLocal()
    try:
        if db.query(Store).count() > 0:
            logger.debug("Atlas: store data already present, skipping seed")
            return

        fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))

        for c in fixture["clusters"]:
            db.execute(
                pg_insert(StoreCluster)
                .values(
                    id=uuid.UUID(c["id"]),
                    label=c["label"],
                    income_tier=c["income_tier"],
                    footfall_tier=c["footfall_tier"],
                    region_code=c["region_code"],
                    region_name_ar=c["region_name_ar"],
                    region_name_en=c["region_name_en"],
                    notes=c.get("notes"),
                    data_source=c.get("data_source", "mock_fixture"),
                )
                .on_conflict_do_nothing()
            )

        for s in fixture["stores"]:
            db.execute(
                pg_insert(Store)
                .values(
                    id=uuid.UUID(s["id"]),
                    name_ar=s["name_ar"],
                    name_en=s["name_en"],
                    chain=StoreChain(s["chain"]),
                    branch_code=s["branch_code"],
                    city_ar=s["city_ar"],
                    city_en=s["city_en"],
                    region_code=s["region_code"],
                    lat=s.get("lat"),
                    lon=s.get("lon"),
                    cluster_id=uuid.UUID(s["cluster_id"]) if s.get("cluster_id") else None,
                    cluster_override=False,
                    data_source=s.get("data_source", "mock_fixture"),
                )
                .on_conflict_do_nothing()
            )

        db.commit()
        logger.info(
            "Atlas: seeded %d clusters and %d stores (illustrative placeholder data — not real GASTAT figures)",
            len(fixture["clusters"]),
            len(fixture["stores"]),
        )
    except Exception:
        logger.exception("Atlas seed failed")
        db.rollback()
    finally:
        db.close()
