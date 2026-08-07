"""
pulse — trend alert module.

Phase 1: ad-count-spike trigger only.

Spike detection requires at least two snapshots per (platform, search_term) separated
by a meaningful time gap. With fixture data (fixed mock counts, idempotent orbit runs)
the counts never change between runs, so the detector will correctly report "no spikes"
rather than producing false positives. Real spike detection only becomes possible once
orbit has accumulated multiple passes with genuinely changing ad counts.

See docs/modules/pulse.md for the full trigger roadmap.
"""
import urllib.parse
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.config import settings
from shared.db import get_db
from shared.models.ad_signal import AdSignal
from shared.models.pulse import PulseAdSnapshot, PulseAlert

router = APIRouter(prefix="/pulse", tags=["pulse"])

_ALERT_TYPE_AD_SPIKE = "ad_count_spike"


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class SnapshotResult(BaseModel):
    signals_captured: int
    snapshotted_at: datetime


class SpikeCandidate(BaseModel):
    platform: str
    search_term: str
    product_id: uuid.UUID | None
    baseline_count: int
    current_count: int
    spike_ratio: float


class ScanResult(BaseModel):
    signals_evaluated: int
    signals_skipped_no_baseline: int
    signals_skipped_below_minimum: int
    spikes_detected: int
    alerts_created: int
    window_hours: int
    min_ratio: float
    min_absolute: int
    candidates: list[SpikeCandidate]


class AlertOut(BaseModel):
    id: uuid.UUID
    alert_type: str
    platform: str
    search_term: str
    product_id: uuid.UUID | None
    baseline_count: int
    current_count: int
    spike_ratio: float
    threshold_ratio: float
    sentinel_url: str
    evidence: dict
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    created_at: datetime


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str


# ---------------------------------------------------------------------------
# Core logic (pure-ish — takes a db session but all business logic is testable)
# ---------------------------------------------------------------------------

def take_snapshot(db: Session) -> SnapshotResult:
    """
    Copy every current AdSignal row into pulse_ad_snapshots.
    Called after each orbit ad pull so we build up the time-series
    that spike detection needs.
    """
    signals = db.query(AdSignal).all()
    now = datetime.now(UTC)

    for sig in signals:
        snap = PulseAdSnapshot(
            id=uuid.uuid4(),
            platform=sig.platform.value,
            search_term=sig.search_term,
            product_id=sig.product_id,
            ad_count_active=sig.ad_count_active,
            snapshotted_at=now,
        )
        db.add(snap)

    db.commit()
    return SnapshotResult(signals_captured=len(signals), snapshotted_at=now)


def scan_for_spikes(db: Session) -> ScanResult:
    """
    Compare the most recent snapshot per (platform, search_term) against a
    rolling baseline from the previous window period.

    Timeline:
      |--- baseline window ---|--- current window ---|  now
      ^                       ^                      ^
    now - 2*W              now - W                  now

    Requires at least one snapshot in each period to evaluate a signal.
    Signals with fewer than min_absolute active ads are skipped to suppress
    noise from very low-volume terms.

    Alert dedup: if an unacknowledged alert already exists for this
    (platform, search_term), a second identical alert is not created.
    This prevents alert storms when pulse/scan is called frequently.
    """
    window_hours = settings.pulse_spike_window_hours
    min_ratio = settings.pulse_spike_min_ratio
    min_absolute = settings.pulse_spike_min_absolute

    now = datetime.now(UTC)
    current_start = now - timedelta(hours=window_hours)
    baseline_start = now - timedelta(hours=window_hours * 2)
    baseline_end = current_start

    # Latest snapshot per signal in the current window
    current_rows = db.execute(
        text("""
            SELECT DISTINCT ON (platform, search_term)
                platform,
                search_term,
                product_id,
                ad_count_active,
                snapshotted_at
            FROM pulse_ad_snapshots
            WHERE snapshotted_at >= :current_start
            ORDER BY platform, search_term, snapshotted_at DESC
        """),
        {"current_start": current_start},
    ).fetchall()

    if not current_rows:
        return ScanResult(
            signals_evaluated=0,
            signals_skipped_no_baseline=0,
            signals_skipped_below_minimum=0,
            spikes_detected=0,
            alerts_created=0,
            window_hours=window_hours,
            min_ratio=min_ratio,
            min_absolute=min_absolute,
            candidates=[],
        )

    # Baseline average per signal
    baseline_rows = db.execute(
        text("""
            SELECT
                platform,
                search_term,
                AVG(ad_count_active)::int AS baseline_avg,
                COUNT(*)                  AS baseline_n
            FROM pulse_ad_snapshots
            WHERE snapshotted_at >= :baseline_start
              AND snapshotted_at <  :baseline_end
            GROUP BY platform, search_term
        """),
        {"baseline_start": baseline_start, "baseline_end": baseline_end},
    ).fetchall()

    baseline_map: dict[tuple, int] = {
        (r.platform, r.search_term): int(r.baseline_avg) for r in baseline_rows
    }

    # Already-open alerts — don't double-alert on the same signal
    open_alert_keys: set[tuple] = set(
        db.execute(
            text("""
                SELECT platform, search_term
                FROM pulse_alerts
                WHERE acknowledged_at IS NULL
                  AND alert_type = :atype
            """),
            {"atype": _ALERT_TYPE_AD_SPIKE},
        ).fetchall()
    )

    no_baseline = 0
    below_min = 0
    candidates: list[SpikeCandidate] = []
    alerts_created = 0

    for row in current_rows:
        key = (row.platform, row.search_term)

        if key not in baseline_map:
            no_baseline += 1
            continue

        current_count = row.ad_count_active
        baseline_count = baseline_map[key]

        if current_count < min_absolute:
            below_min += 1
            continue

        # Guard against division by zero (baseline was 0 or rounded to 0)
        if baseline_count <= 0:
            spike_ratio = float(current_count)
        else:
            spike_ratio = current_count / baseline_count

        if spike_ratio < min_ratio:
            continue

        candidates.append(
            SpikeCandidate(
                platform=row.platform,
                search_term=row.search_term,
                product_id=row.product_id,
                baseline_count=baseline_count,
                current_count=current_count,
                spike_ratio=round(spike_ratio, 4),
            )
        )

        if key in open_alert_keys:
            # Unacknowledged alert already open for this signal — skip
            continue

        sentinel_url = f"/sentinel/search?q={urllib.parse.quote(row.search_term)}"

        evidence = {
            "window_hours": window_hours,
            "baseline_period": {
                "start": baseline_start.isoformat(),
                "end": baseline_end.isoformat(),
            },
            "current_period": {
                "start": current_start.isoformat(),
                "end": now.isoformat(),
            },
            "baseline_count": baseline_count,
            "current_count": current_count,
            "spike_ratio": round(spike_ratio, 4),
            "threshold_ratio": min_ratio,
            "platform": row.platform,
            "search_term": row.search_term,
            "product_id": str(row.product_id) if row.product_id else None,
        }

        alert = PulseAlert(
            id=uuid.uuid4(),
            alert_type=_ALERT_TYPE_AD_SPIKE,
            platform=row.platform,
            search_term=row.search_term,
            product_id=row.product_id,
            baseline_count=baseline_count,
            current_count=current_count,
            spike_ratio=spike_ratio,
            threshold_ratio=min_ratio,
            sentinel_url=sentinel_url,
            evidence_json=evidence,
        )
        db.add(alert)
        alerts_created += 1

    db.commit()

    return ScanResult(
        signals_evaluated=len(current_rows),
        signals_skipped_no_baseline=no_baseline,
        signals_skipped_below_minimum=below_min,
        spikes_detected=len(candidates),
        alerts_created=alerts_created,
        window_hours=window_hours,
        min_ratio=min_ratio,
        min_absolute=min_absolute,
        candidates=candidates,
    )


def _alert_to_out(a: PulseAlert) -> AlertOut:
    return AlertOut(
        id=a.id,
        alert_type=a.alert_type,
        platform=a.platform,
        search_term=a.search_term,
        product_id=a.product_id,
        baseline_count=a.baseline_count,
        current_count=a.current_count,
        spike_ratio=float(a.spike_ratio),
        threshold_ratio=float(a.threshold_ratio),
        sentinel_url=a.sentinel_url,
        evidence=a.evidence_json,
        acknowledged_at=a.acknowledged_at,
        acknowledged_by=a.acknowledged_by,
        created_at=a.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
def health():
    return {"status": "ok", "module": "pulse"}


@router.get("/config")
def get_config():
    """Return the active spike detection thresholds — configurable via .env."""
    return {
        "pulse_spike_window_hours": settings.pulse_spike_window_hours,
        "pulse_spike_min_ratio": settings.pulse_spike_min_ratio,
        "pulse_spike_min_absolute": settings.pulse_spike_min_absolute,
        "notes": {
            "window_hours": "Snapshots within this window are 'current'; the equal-length window before it is the baseline.",
            "min_ratio": "Alert when current_count / baseline_avg >= this value.",
            "min_absolute": "Ignore signals with current_count below this (suppresses 1→2 noise).",
        },
    }


@router.post("/snapshot", response_model=SnapshotResult)
def snapshot(db: Session = Depends(get_db)):
    """
    Capture the current state of all AdSignal rows into pulse_ad_snapshots.
    Call this after each orbit ad pull (or manually to seed the time-series).
    Returns how many signals were snapshotted.
    """
    return take_snapshot(db)


@router.post("/scan", response_model=ScanResult)
def scan(db: Session = Depends(get_db)):
    """
    Run spike detection across all tracked ad signals.
    Compares the most recent snapshot (within the configured window) against
    the rolling baseline from the window before it.

    With fixture data and idempotent orbit runs the counts never change, so this
    will correctly return spikes_detected=0. Real spikes only appear once orbit
    has accumulated multiple passes with genuinely changing ad_count_active values.
    """
    return scan_for_spikes(db)


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    acknowledged: bool | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    List alerts. Pass ?acknowledged=false for active-only, ?acknowledged=true
    for historical. Omit to get all.
    """
    q = db.query(PulseAlert).order_by(PulseAlert.created_at.desc())
    if acknowledged is False:
        q = q.filter(PulseAlert.acknowledged_at.is_(None))
    elif acknowledged is True:
        q = q.filter(PulseAlert.acknowledged_at.isnot(None))
    return [_alert_to_out(a) for a in q.limit(limit).all()]


@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: uuid.UUID, db: Session = Depends(get_db)):
    a = db.query(PulseAlert).filter(PulseAlert.id == alert_id).first()
    if a is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return _alert_to_out(a)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(
    alert_id: uuid.UUID,
    body: AcknowledgeRequest,
    db: Session = Depends(get_db),
):
    a = db.query(PulseAlert).filter(PulseAlert.id == alert_id).first()
    if a is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    if a.acknowledged_at is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Alert already acknowledged by {a.acknowledged_by} at {a.acknowledged_at}",
        )
    a.acknowledged_at = datetime.now(UTC)
    a.acknowledged_by = body.acknowledged_by
    db.commit()
    db.refresh(a)
    return _alert_to_out(a)
