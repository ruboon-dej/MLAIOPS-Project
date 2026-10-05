"""
CI test for failure demonstration 2 (build-time loop: bad input -> validation
fails -> CI test fails -> deployment blocked). Each test here corresponds to
one of the checks in src/validate.py.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from validate import validate, REQUIRED_COLUMNS, TARGET  # noqa: E402


def _good_df(n=10) -> pd.DataFrame:
    base = {
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "occupancy": list(range(n)),
    }
    for col in REQUIRED_COLUMNS:
        if col not in base and col != TARGET:
            base[col] = [0] * n
    # target = occupancy shifted by -1, consistent with validate.py's leakage check
    base[TARGET] = base["occupancy"][1:] + [base["occupancy"][-1]]
    return pd.DataFrame(base)


def test_good_data_passes():
    df = _good_df()
    assert validate(df) == []


def test_missing_required_column_fails():
    df = _good_df().drop(columns=["arrivals_1h"])
    problems = validate(df)
    assert any("missing required columns" in p for p in problems)


def test_entirely_null_target_fails():
    df = _good_df()
    df[TARGET] = None
    problems = validate(df)
    assert any("entirely null" in p for p in problems)


def test_duplicate_timestamps_fail():
    """This is THE test for failure demo 2's schema half: feeding data with
    a duplicate timestamp must be caught before training, not after."""
    df = _good_df()
    df.loc[1, "timestamp"] = df.loc[0, "timestamp"]
    problems = validate(df)
    assert any("duplicate" in p for p in problems)


def test_out_of_order_timestamps_fail():
    df = _good_df()
    df = df.iloc[::-1].reset_index(drop=True)  # reverse the order
    problems = validate(df)
    assert any("increasing" in p for p in problems)


def test_missing_values_fail():
    df = _good_df()
    df.loc[2, "occupancy"] = None
    problems = validate(df)
    assert any("missing values" in p for p in problems)


def test_leakage_mismatch_detected():
    """If occupancy_1h_ahead doesn't actually correspond to the next row's
    occupancy, that signals the target was built looking at the wrong data —
    a leakage/misalignment bug, not just noise."""
    df = _good_df()
    df[TARGET] = df[TARGET].sample(frac=1, random_state=1).reset_index(drop=True)
    problems = validate(df)
    assert any("leakage" in p for p in problems)


def test_unparseable_timestamp_fails():
    df = _good_df()
    df["timestamp"] = ["not-a-date"] * len(df)
    problems = validate(df)
    assert any("does not parse" in p for p in problems)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
