"""
Data validation stage: DVC -> validate -> train (architecture.md build flow).

Checks, in order, so the first failure found is the one reported:
  1. required columns present
  2. target column present and not entirely null
  3. timestamp column parses and is strictly increasing (no gaps checked here,
     only ordering + duplicates)
  4. no duplicate timestamps
  5. no missing values in required columns
  6. no obvious leakage: occupancy_1h_ahead must not equal occupancy shifted
     the wrong way (a simple sanity check, not a proof)

Exit code 0 = pass, 1 = fail. This is what `make validate` and the CI test
call. Failure demo 2 feeds bad input through this script.
"""
from __future__ import annotations

import sys
import argparse
import pandas as pd

REQUIRED_COLUMNS = [
    "timestamp", "occupancy", "arrivals_1h", "arrivals_3h", "arrivals_6h",
    "departures_1h", "departures_3h", "departures_6h",
    "triage_1_count", "triage_2_count", "triage_3_count", "triage_4_count", "triage_5_count",
    "mean_current_los_hours", "median_current_los_hours",
    "long_stay_4h_count", "long_stay_8h_count",
    "hour_of_day", "day_of_week", "is_weekend",
    "occupancy_1h_ahead",
]

TARGET = "occupancy_1h_ahead"


class ValidationError(Exception):
    pass


def validate(df: pd.DataFrame) -> list[str]:
    """Returns a list of problems found. Empty list = valid."""
    problems = []

    # 1. required columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        problems.append(f"missing required columns: {missing_cols}")
        # Can't safely check anything else without the columns that matter most.
        if "timestamp" in missing_cols or TARGET in missing_cols:
            return problems

    # 2. target present and not entirely null
    if TARGET in df.columns:
        if df[TARGET].isna().all():
            problems.append(f"target column '{TARGET}' is entirely null")

    # 3. timestamp parses and is strictly increasing
    if "timestamp" in df.columns:
        try:
            ts = pd.to_datetime(df["timestamp"])
        except Exception as e:
            problems.append(f"timestamp column does not parse as datetime: {e}")
            ts = None
        if ts is not None:
            if not ts.is_monotonic_increasing:
                problems.append("timestamp column is not strictly increasing")
            # 4. duplicate timestamps
            dup_count = ts.duplicated().sum()
            if dup_count > 0:
                problems.append(f"{dup_count} duplicate timestamp(s) found")

    # 5. missing values in required columns that exist
    present_required = [c for c in REQUIRED_COLUMNS if c in df.columns]
    null_counts = df[present_required].isna().sum()
    bad_cols = null_counts[null_counts > 0]
    if len(bad_cols) > 0:
        problems.append(f"missing values found in: {bad_cols.to_dict()}")

    # 6. obvious leakage sanity check: occupancy_1h_ahead at row i should equal
    #    occupancy at row i+1 for a correctly-shifted target, in this
    #    simulated, evenly-spaced dataset. A mismatch rate above 5% signals
    #    the target was built from the wrong direction (using future-at-prediction-time
    #    data) or the file has been reordered/corrupted.
    if TARGET in df.columns and "occupancy" in df.columns and len(df) > 1:
        shifted_actual = df["occupancy"].shift(-1)
        comparable = df.iloc[:-1]
        mismatch = (comparable[TARGET] != shifted_actual.iloc[:-1]).mean()
        if mismatch > 0.05:
            problems.append(
                f"possible leakage/misalignment: {mismatch:.1%} of rows have "
                f"'{TARGET}' that doesn't match the next row's occupancy"
            )

    return problems


def main():
    parser = argparse.ArgumentParser(description="Validate ED occupancy data before training.")
    parser.add_argument("path", help="Path to the CSV file to validate")
    parser.add_argument("--quiet", action="store_true", help="Only print on failure")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.path)
    except Exception as e:
        print(f"FAIL: could not read {args.path}: {e}")
        sys.exit(1)

    problems = validate(df)

    if problems:
        print(f"FAIL: {len(problems)} problem(s) found in {args.path}")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    if not args.quiet:
        print(f"PASS: {args.path} ({len(df)} rows) looks valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
