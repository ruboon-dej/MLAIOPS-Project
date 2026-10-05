"""
make score

One scoring pass, as if triggered by Cloud Scheduler -> Cloud Run Job.
  1. load the latest live row (from the replay feed)
  2. check freshness -> normal / degraded / refuse
  3. if refuse: emit the stale metric, write nothing new, exit nonzero
  4. else: load the model, predict, write the forecast report, emit metrics

This is deliberately a single run-to-completion script with no loop, so it
maps directly onto a Cloud Run Job execution (which runs once and exits).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import mlflow.sklearn
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from features import build_features  # noqa: E402
from freshness import check_freshness, FreshnessState  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent))
from cloudlayer import get_adapter  # noqa: E402

LIVE_FILE = Path("data/live/latest.csv")
HISTORY_FILE = Path("data/live/history.csv")
MODEL_URI = Path(os.environ.get("MODEL_URI", "data/models/latest"))
REPORT_DIR = Path("data/reports")
DEADLINE_SECONDS = int(os.environ.get("SCORE_DEADLINE_MINUTES", 5)) * 60


def main():
    start = time.monotonic()
    adapter = get_adapter()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not LIVE_FILE.exists():
        print("REFUSE: no live feed found — is `make replay` running?", file=sys.stderr)
        adapter.emit_metric("ed_forecast_state", 0, {"state": "refuse", "reason": "no_feed"})
        sys.exit(1)

    latest = pd.read_csv(LIVE_FILE, parse_dates=["timestamp"]).iloc[0]
    result = check_freshness(latest["timestamp"].to_pydatetime())

    adapter.emit_metric("ed_data_age_minutes", result.age_minutes, {"state": result.state.value})

    if not result.should_score:
        print(
            f"REFUSE: data age {result.age_minutes:.1f} min exceeds "
            f"{result.threshold_stale} min threshold — not scoring",
            file=sys.stderr,
        )
        adapter.emit_metric("ed_forecast_state", 0, {"state": "refuse"})
        sys.exit(1)

    if result.state == FreshnessState.DEGRADED:
        print(
            f"WARNING: data age {result.age_minutes:.1f} min is degraded "
            f"(over {result.threshold_ok} min) — scoring anyway, flagged in report",
            file=sys.stderr,
        )

    # Need enough history for feature columns that reference recent hours.
    history = pd.read_csv(HISTORY_FILE, parse_dates=["timestamp"])
    features = build_features(history.tail(1))

    model = mlflow.sklearn.load_model(str(MODEL_URI / "sklearn_model"))
    prediction = float(model.predict(features)[0])

    elapsed = time.monotonic() - start

    report = {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "input_timestamp": latest["timestamp"].isoformat(),
        "freshness_state": result.state.value,
        "data_age_minutes": round(result.age_minutes, 2),
        "current_occupancy": int(latest["occupancy"]),
        "predicted_occupancy_1h_ahead": round(prediction, 1),
        "scoring_latency_seconds": round(elapsed, 2),
        "within_deadline": elapsed <= DEADLINE_SECONDS,
    }

    report_path = REPORT_DIR / f"forecast_{int(time.time())}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    adapter.upload(str(report_path), f"reports/{report_path.name}")

    adapter.emit_metric("ed_forecast_state", 1, {"state": result.state.value})
    adapter.emit_metric("ed_scoring_latency_seconds", elapsed, {})
    adapter.emit_metric("ed_predicted_occupancy", prediction, {})

    print(json.dumps(report, indent=2))

    if not report["within_deadline"]:
        print(
            f"WARNING: scoring took {elapsed:.1f}s, over the "
            f"{DEADLINE_SECONDS}s deadline (architecture.md section 9)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
