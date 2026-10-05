"""
CI test for failure demonstration 1 (architecture.md "Failure demonstrations").
This test fails against code with no freshness guard, and passes once the
guard in src/freshness.py exists — exactly what the brief requires
("tests that can actually fail").
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest  # noqa: E402

os.environ.setdefault("FRESH_OK_MINUTES", "60")
os.environ.setdefault("FRESH_STALE_MINUTES", "120")

from freshness import check_freshness, FreshnessState  # noqa: E402


def test_fresh_data_is_normal():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    latest = now - timedelta(minutes=10)
    result = check_freshness(latest, now=now)
    assert result.state == FreshnessState.NORMAL
    assert result.should_score


def test_data_at_exactly_ok_boundary_is_normal():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    latest = now - timedelta(minutes=60)
    result = check_freshness(latest, now=now)
    assert result.state == FreshnessState.NORMAL


def test_data_between_thresholds_is_degraded():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    latest = now - timedelta(minutes=90)
    result = check_freshness(latest, now=now)
    assert result.state == FreshnessState.DEGRADED
    assert result.should_score  # degraded still scores, per the spec


def test_data_past_stale_threshold_is_refused():
    """This is THE test for failure demo 1: stop the replay feed, data
    goes stale past 120 minutes, the pipeline must refuse to score."""
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    latest = now - timedelta(minutes=121)
    result = check_freshness(latest, now=now)
    assert result.state == FreshnessState.REFUSE
    assert not result.should_score


def test_future_timestamp_is_refused_not_silently_accepted():
    """Clock/timezone bugs should refuse loudly, not score confidently on
    bad data (architecture.md section 9, 'Time zones')."""
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    latest = now + timedelta(minutes=30)
    result = check_freshness(latest, now=now)
    assert result.state == FreshnessState.REFUSE


def test_invalid_threshold_config_raises():
    os.environ["FRESH_OK_MINUTES"] = "120"
    os.environ["FRESH_STALE_MINUTES"] = "60"  # stale < ok, a misconfiguration
    try:
        with pytest.raises(ValueError):
            check_freshness(datetime.now(timezone.utc))
    finally:
        os.environ["FRESH_OK_MINUTES"] = "60"
        os.environ["FRESH_STALE_MINUTES"] = "120"
