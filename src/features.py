"""
Shared feature preparation. train.py and score.py both import this so the
features used at training time and scoring time can never silently drift
apart from each other (a common real-world source of production bugs).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TARGET = "occupancy_1h_ahead"

FEATURE_COLUMNS = [
    "occupancy",
    "arrivals_1h", "arrivals_3h", "arrivals_6h",
    "departures_1h", "departures_3h", "departures_6h",
    "triage_1_count", "triage_2_count", "triage_3_count", "triage_4_count", "triage_5_count",
    "mean_current_los_hours", "median_current_los_hours",
    "long_stay_4h_count", "long_stay_8h_count",
    "hour_sin", "hour_cos",
    "is_weekend",
]


def add_cyclical_hour(df: pd.DataFrame) -> pd.DataFrame:
    """hour_of_day is 0-23 and looks linear to a model but is cyclical
    (hour 23 is one hour from hour 0). Encode it the same way the original
    XAI project did."""
    df = df.copy()
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a dataframe with exactly FEATURE_COLUMNS, in order.
    Only uses data that would be available at prediction time (no leakage):
    every column here describes the current or past hour, never the future."""
    df = add_cyclical_hour(df)
    return df[FEATURE_COLUMNS]


def persistence_baseline(df: pd.DataFrame) -> pd.Series:
    """The naive baseline: predict next hour's occupancy = current occupancy.
    Any trained model must be compared against this. Oil/ED forecasting is
    hard to beat; report the comparison honestly rather than hiding it."""
    return df["occupancy"]
