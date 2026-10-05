"""
Freshness guard — three states, thresholds read from cloud.env, never hardcoded.
Matches the table in architecture.md "Freshness states".

  age <= FRESH_OK_MINUTES                      -> normal   (score + publish)
  FRESH_OK_MINUTES < age <= FRESH_STALE_MINUTES -> degraded (score + publish, flagged)
  age > FRESH_STALE_MINUTES                     -> refuse   (do not score, alert)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class FreshnessState(str, Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    REFUSE = "refuse"


@dataclass
class FreshnessResult:
    state: FreshnessState
    age_minutes: float
    threshold_ok: int
    threshold_stale: int

    @property
    def should_score(self) -> bool:
        return self.state != FreshnessState.REFUSE


def load_thresholds() -> tuple[int, int]:
    """Reads FRESH_OK_MINUTES / FRESH_STALE_MINUTES from the environment.
    Falls back to the documented defaults (60 / 120) if unset — but a real
    deployment should always set these via cloud.env, not rely on the default.
    """
    ok = int(os.environ.get("FRESH_OK_MINUTES", 60))
    stale = int(os.environ.get("FRESH_STALE_MINUTES", 120))
    if stale <= ok:
        raise ValueError(
            f"FRESH_STALE_MINUTES ({stale}) must be greater than FRESH_OK_MINUTES ({ok})"
        )
    return ok, stale


def check_freshness(latest_timestamp: datetime, now: datetime | None = None) -> FreshnessResult:
    """latest_timestamp: the newest row's timestamp in the data being scored.
    now: defaults to current UTC time; pass explicitly in tests.
    """
    ok, stale = load_thresholds()

    if now is None:
        now = datetime.now(timezone.utc)

    # Normalize both to naive-UTC-equivalent comparison to avoid tz mismatches
    # being silently wrong (see architecture.md section 9, "Time zones").
    if latest_timestamp.tzinfo is None:
        latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_minutes = (now - latest_timestamp).total_seconds() / 60.0

    if age_minutes < 0:
        # Data timestamped in the future — treat as refuse, this is a clock
        # or timezone bug, not a thing to silently accept.
        state = FreshnessState.REFUSE
    elif age_minutes <= ok:
        state = FreshnessState.NORMAL
    elif age_minutes <= stale:
        state = FreshnessState.DEGRADED
    else:
        state = FreshnessState.REFUSE

    return FreshnessResult(
        state=state,
        age_minutes=age_minutes,
        threshold_ok=ok,
        threshold_stale=stale,
    )
