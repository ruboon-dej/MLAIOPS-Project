"""
Pipeline-level guard for the stale-feed failure: score.py must refuse to score
when the latest row is older than FRESH_STALE_MINUTES. Unit tests on
check_freshness() alone would still pass if the branch in score.py were deleted.
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCORE = Path(__file__).parent.parent / "src" / "score.py"


def _run_score(tmp_path, age_minutes):
    live = tmp_path / "data" / "live"
    live.mkdir(parents=True)
    ts = (datetime.now(timezone.utc) - timedelta(minutes=age_minutes)).isoformat()
    for name in ("latest.csv", "history.csv"):
        (live / name).write_text(f"timestamp,occupancy\n{ts},12\n")
    env = {
        **os.environ,
        "CLOUD_PROVIDER": "local",
        "LIVE_FEED_SOURCE": "local",
        "FRESH_OK_MINUTES": "60",
        "FRESH_STALE_MINUTES": "120",
    }
    return subprocess.run(
        [sys.executable, str(SCORE)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )


def test_stale_feed_is_not_scored(tmp_path):
    proc = _run_score(tmp_path, age_minutes=180)
    assert proc.returncode != 0
    assert "REFUSE: data age" in proc.stderr
    assert not list((tmp_path / "data" / "reports").glob("forecast_*.json"))


def test_fresh_feed_passes_the_guard(tmp_path):
    proc = _run_score(tmp_path, age_minutes=5)
    assert "REFUSE" not in proc.stderr
