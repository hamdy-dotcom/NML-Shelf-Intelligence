"""
Atlas — store cluster map.

Exposes StoreCluster and Store data for downstream consumption by oracle and prism.
Phase 1: read endpoints + manual cluster override. Clustering algorithm (GASTAT-driven
re-assignment) comes once real regional data is loaded.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.config import settings
from shared.db import get_db
from shared.models.store import Store, StoreCluster

router = APIRouter(prefix="/atlas")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ClusterOverrideBody(BaseModel):
    cluster_id: uuid.UUID
    overridden_by: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cluster_to_dict(c: StoreCluster) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "label": c.label,
        "income_tier": c.income_tier,
        "footfall_tier": c.footfall_tier,
        "region_code": c.region_code,
        "region_name_ar": c.region_name_ar,
        "region_name_en": c.region_name_en,
        "notes": c.notes,
        "data_source": c.data_source,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _store_to_dict(s: Store, include_cluster: bool = False, cluster: StoreCluster | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": str(s.id),
        "name_ar": s.name_ar,
        "name_en": s.name_en,
        "chain": s.chain.value,
        "branch_code": s.branch_code,
        "city_ar": s.city_ar,
        "city_en": s.city_en,
        "region_code": s.region_code,
        "lat": float(s.lat) if s.lat is not None else None,
        "lon": float(s.lon) if s.lon is not None else None,
        "cluster_id": str(s.cluster_id) if s.cluster_id else None,
        "cluster_override": s.cluster_override,
        "cluster_override_by": s.cluster_override_by,
        "cluster_override_at": s.cluster_override_at.isoformat() if s.cluster_override_at else None,
        "data_source": s.data_source,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
    if include_cluster and cluster:
        d["cluster"] = _cluster_to_dict(cluster)
    return d


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/clusters")
def list_clusters(
    region_code: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List all store clusters, optionally filtered by GASTAT region code."""
    q = db.query(StoreCluster)
    if region_code:
        q = q.filter(StoreCluster.region_code == region_code)
    clusters = q.order_by(StoreCluster.region_code, StoreCluster.label).all()

    # Attach store counts per cluster
    counts_rows = db.execute(
        text("SELECT cluster_id, COUNT(*) AS n FROM stores WHERE cluster_id IS NOT NULL GROUP BY cluster_id")
    ).fetchall()
    counts = {str(r.cluster_id): r.n for r in counts_rows}

    return {
        "mock_mode": settings.atlas_mock_mode,
        "total": len(clusters),
        "clusters": [
            {**_cluster_to_dict(c), "store_count": counts.get(str(c.id), 0)}
            for c in clusters
        ],
    }


@router.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Cluster detail with its member stores."""
    cluster = db.get(StoreCluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    stores = db.query(Store).filter(Store.cluster_id == cluster_id).order_by(Store.name_en).all()

    return {
        **_cluster_to_dict(cluster),
        "stores": [_store_to_dict(s) for s in stores],
    }


@router.get("/stores")
def list_stores(
    chain: str | None = None,
    cluster_id: uuid.UUID | None = None,
    region_code: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List stores, filterable by chain, cluster, or GASTAT region code."""
    q = db.query(Store)
    if chain:
        q = q.filter(Store.chain == chain)
    if cluster_id:
        q = q.filter(Store.cluster_id == cluster_id)
    if region_code:
        q = q.filter(Store.region_code == region_code)
    stores = q.order_by(Store.chain, Store.name_en).all()

    # Load clusters in one query for inline embedding
    cluster_ids = {s.cluster_id for s in stores if s.cluster_id}
    clusters: dict[uuid.UUID, StoreCluster] = {}
    if cluster_ids:
        for c in db.query(StoreCluster).filter(StoreCluster.id.in_(cluster_ids)).all():
            clusters[c.id] = c

    return {
        "mock_mode": settings.atlas_mock_mode,
        "total": len(stores),
        "stores": [
            _store_to_dict(s, include_cluster=True, cluster=clusters.get(s.cluster_id))
            for s in stores
        ],
    }


@router.get("/stores/{store_id}")
def get_store(store_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Store detail with its cluster embedded."""
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    cluster = db.get(StoreCluster, store.cluster_id) if store.cluster_id else None
    return _store_to_dict(store, include_cluster=True, cluster=cluster)


@router.patch("/stores/{store_id}/cluster")
def override_cluster(
    store_id: uuid.UUID,
    body: ClusterOverrideBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Manually reassign a store to a different cluster.
    Sets cluster_override=True and logs who made the change and when.
    The override flag lets downstream modules know this assignment was human-verified.
    """
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    cluster = db.get(StoreCluster, body.cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    store.cluster_id = body.cluster_id
    store.cluster_override = True
    store.cluster_override_by = body.overridden_by
    store.cluster_override_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "store_id": str(store.id),
        "cluster_id": str(store.cluster_id),
        "cluster_label": cluster.label,
        "cluster_override": True,
        "cluster_override_by": store.cluster_override_by,
        "cluster_override_at": store.cluster_override_at.isoformat(),
    }
