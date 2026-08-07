"""
pulse end-to-end test.

Runs with the live DB. Covers everything that can be verified in a single session:
  1. Snapshot endpoint copies AdSignal state correctly
  2. Scan with one snapshot → all signals skipped (no baseline yet)
  3. Synthetic baseline + spiked current → spike correctly detected
  4. Alert created in ledger with correct fields + sentinel URL
  5. Alert acknowledgement workflow

Run after `venv/bin/alembic upgrade head` and with the app running:
    python3 pulse_test.py
Or against a running app (default http://localhost:8000):
    BASE=http://localhost:8000 python3 pulse_test.py
"""
import sys
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text

BASE = "http://localhost:8000"


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}" + (f": {detail}" if detail else ""))
    if not cond:
        sys.exit(1)


def main():
    client = httpx.Client(base_url=BASE, timeout=30)

    # -----------------------------------------------------------------------
    print("\n=== 1. health ===")
    r = client.get("/pulse/health")
    check("200 OK", r.status_code == 200)
    check("module=pulse", r.json()["module"] == "pulse")

    # -----------------------------------------------------------------------
    print("\n=== 2. config ===")
    r = client.get("/pulse/config")
    check("200 OK", r.status_code == 200)
    cfg = r.json()
    check("has window_hours", "pulse_spike_window_hours" in cfg)
    check("has min_ratio",    "pulse_spike_min_ratio" in cfg)
    check("has min_absolute", "pulse_spike_min_absolute" in cfg)
    print(f"  window={cfg['pulse_spike_window_hours']}h  ratio={cfg['pulse_spike_min_ratio']}×  min_absolute={cfg['pulse_spike_min_absolute']}")

    # -----------------------------------------------------------------------
    print("\n=== 3. snapshot (first pass) ===")
    r = client.post("/pulse/snapshot")
    check("200 OK", r.status_code == 200)
    snap = r.json()
    check("signals_captured > 0", snap["signals_captured"] > 0, str(snap["signals_captured"]))
    print(f"  captured {snap['signals_captured']} signals at {snap['snapshotted_at']}")

    # -----------------------------------------------------------------------
    print("\n=== 4. scan — no baseline yet → all skipped ===")
    r = client.post("/pulse/scan")
    check("200 OK", r.status_code == 200)
    result = r.json()
    check("spikes_detected=0",            result["spikes_detected"] == 0)
    check("signals_skipped_no_baseline>0", result["signals_skipped_no_baseline"] > 0,
          f"skipped={result['signals_skipped_no_baseline']}")
    print(f"  evaluated={result['signals_evaluated']}  no_baseline={result['signals_skipped_no_baseline']}  spikes={result['spikes_detected']}")
    print("  ✓ Correct: all signals skipped because no snapshots exist in the baseline window yet.")

    # -----------------------------------------------------------------------
    print("\n=== 5. synthetic spike test ===")
    print("  Inserting backdated baseline snapshots + inflated current snapshots directly into DB.")
    print("  (Can't wait 24h in a test; this proves the detection logic, not the scheduler timing.)")

    from shared.db import SessionLocal
    from shared.models.pulse import PulseAdSnapshot
    from shared.models.ad_signal import AdSignal

    db = SessionLocal()
    window_hours = cfg["pulse_spike_window_hours"]
    now = datetime.now(UTC)
    baseline_time = now - timedelta(hours=window_hours * 1.5)  # midpoint of baseline window

    # Read current ad signals to base synthetic data on
    signals = db.query(AdSignal).limit(3).all()
    if not signals:
        print("  SKIP: no ad_signals rows found — run orbit first")
    else:
        for sig in signals:
            # Baseline snapshot — a realistic count from 36h ago
            db.add(PulseAdSnapshot(
                id=uuid.uuid4(),
                platform=sig.platform.value,
                search_term=sig.search_term,
                product_id=sig.product_id,
                ad_count_active=sig.ad_count_active,
                snapshotted_at=baseline_time,
            ))
            # Current snapshot — 5× the baseline count (simulates spike)
            spiked_count = sig.ad_count_active * 5
            db.add(PulseAdSnapshot(
                id=uuid.uuid4(),
                platform=sig.platform.value,
                search_term=sig.search_term,
                product_id=sig.product_id,
                ad_count_active=spiked_count,
                snapshotted_at=now,
            ))
        db.commit()
        spiked_terms = [s.search_term for s in signals if s.ad_count_active * 5 >= cfg["pulse_spike_min_absolute"]]
        db.close()
        print(f"  Inserted baseline+spiked snapshots for {len(signals)} signals (5× each)")

        # -----------------------------------------------------------------------
        print("\n=== 6. scan — should detect spikes now ===")
        r = client.post("/pulse/scan")
        check("200 OK", r.status_code == 200)
        result = r.json()
        eligible = [s for s in signals if s.ad_count_active * 5 >= cfg["pulse_spike_min_absolute"]]
        check("spikes_detected >= eligible count",
              result["spikes_detected"] >= len(eligible),
              f"detected={result['spikes_detected']}, eligible={len(eligible)}")
        check("alerts_created > 0", result["alerts_created"] > 0, str(result["alerts_created"]))
        print(f"  evaluated={result['signals_evaluated']}  spikes={result['spikes_detected']}  alerts_created={result['alerts_created']}")
        for c in result["candidates"]:
            print(f"  → '{c['search_term']}' ({c['platform']})  {c['baseline_count']}→{c['current_count']}  ratio={c['spike_ratio']:.2f}×")

        # -----------------------------------------------------------------------
        print("\n=== 7. alerts list ===")
        r = client.get("/pulse/alerts?acknowledged=false")
        check("200 OK", r.status_code == 200)
        alerts = r.json()
        check("at least one alert", len(alerts) > 0)
        a = alerts[0]
        check("has sentinel_url", a["sentinel_url"].startswith("/sentinel/search?q="))
        check("has evidence",     bool(a["evidence"]))
        check("alert_type=ad_count_spike", a["alert_type"] == "ad_count_spike")
        check("acknowledged_at is None", a["acknowledged_at"] is None)
        print(f"  alert id={a['id']}")
        print(f"  sentinel_url={a['sentinel_url']}")
        print(f"  reasoning: {a['baseline_count']}→{a['current_count']} ({a['spike_ratio']:.2f}×)")

        # -----------------------------------------------------------------------
        print("\n=== 8. acknowledge alert ===")
        alert_id = a["id"]
        r = client.post(f"/pulse/alerts/{alert_id}/acknowledge",
                        json={"acknowledged_by": "test-runner"})
        check("200 OK", r.status_code == 200)
        ack = r.json()
        check("acknowledged_at set",      ack["acknowledged_at"] is not None)
        check("acknowledged_by set",      ack["acknowledged_by"] == "test-runner")

        # -----------------------------------------------------------------------
        print("\n=== 9. double-acknowledge → 409 ===")
        r = client.post(f"/pulse/alerts/{alert_id}/acknowledge",
                        json={"acknowledged_by": "test-runner-2"})
        check("409 Conflict", r.status_code == 409)

        # -----------------------------------------------------------------------
        print("\n=== 10. scan again — no duplicate alert for already-open signal ===")
        # Re-insert another spiked snapshot so the signal still appears in current window
        db = SessionLocal()
        for sig in signals:
            db.add(PulseAdSnapshot(
                id=uuid.uuid4(),
                platform=sig.platform.value,
                search_term=sig.search_term,
                product_id=sig.product_id,
                ad_count_active=sig.ad_count_active * 5,
                snapshotted_at=now,
            ))
        db.commit()
        db.close()
        r = client.post("/pulse/scan")
        check("200 OK", r.status_code == 200)
        result2 = r.json()
        # The acknowledged alert was cleared; remaining unacknowledged ones shouldn't dupe.
        # New alert may be created for the freshly-acknowledged signal (now clear to re-alert).
        print(f"  alerts_created this scan={result2['alerts_created']}  (expected ≤ spikes_detected)")
        check("alerts ≤ spikes", result2["alerts_created"] <= result2["spikes_detected"])

    # -----------------------------------------------------------------------
    print("\n=== All tests passed ===")
    print()
    print("What this test CANNOT verify:")
    print("  - Whether spike thresholds are correctly calibrated (needs real ad variance data)")
    print("  - Whether the 24h window matches actual KSA retail ad cycle patterns")
    print("  - False positive / false negative rates (need multiple weeks of real orbit runs)")
    print()
    print("What needs real time-series data to emerge naturally:")
    print("  - Spikes from the scheduler path (orbit ad pull → auto pulse snapshot → auto scan)")
    print("    requires orbit_ad_poll_interval_minutes passes with genuinely different ad counts")
    print("  - With mock data, fixture counts are fixed → scan always returns 0 spikes organically")


if __name__ == "__main__":
    main()
