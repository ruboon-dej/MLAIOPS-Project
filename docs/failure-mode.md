# Deliberate failure: stale or frozen upstream feed

## What we engineered
The replay source is stopped, so the scheduled job keeps seeing the last row it was given. The forecasts would still look plausible, which is what makes this failure dangerous. The pipeline should detect the age of the data, flag it, and refuse to score once it is too old.

## Guard
`src/freshness.py` defines three states from the age of the latest row: normal up to 60 minutes, degraded (scored and flagged) up to 120 minutes, refused beyond that. Thresholds come from `FRESH_OK_MINUTES` and `FRESH_STALE_MINUTES`. On refusal `src/score.py` emits the `ed_forecast_state` metric, writes no forecast and exits nonzero. The guard refused a real run on 2026-10-08 at a data age of 122.1 minutes, and the stale-data alert was verified firing by email the same day.

## What the failure revealed
The first version of the guard was covered only by unit tests on `check_freshness()`. Removing the refusal branch from `score.py` would have left every test green, so the pipeline could have scored stale data in production while CI passed. We closed this with `tests/test_score_refusal.py`, which runs `score.py` end to end on a feed whose latest row is three hours old and asserts a nonzero exit, a `REFUSE` message and no forecast file. A twin test with a fresh feed guards against a test that passes only because scoring is broken.

## Evidence the tests can fail
- Disabling the refusal branch in `score.py`: `1 failed, 1 passed` in `tests/test_score_refusal.py`.
- Weakening the refuse state in `freshness.py`: three tests fail in `tests/test_freshness.py`.

## Scope
We guard against stale data only. We do not claim a distribution or frozen-column check.
