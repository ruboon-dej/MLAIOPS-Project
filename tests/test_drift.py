import numpy as np
import pandas as pd

from src.drift import compute


def make(n, shift=0.0, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "occupancy": rng.normal(30 + shift, 5, n),
            "arrivals_1h": rng.poisson(6 + shift / 3, n).astype(float),
            "departures_1h": rng.poisson(6, n).astype(float),
        }
    )


def test_same_distribution_is_ok():
    assert compute(make(2000, seed=1), make(500, seed=2))["decision"] == "ok"


def test_shifted_distribution_recommends_retrain():
    result = compute(make(2000, seed=1), make(500, shift=15, seed=3))
    assert result["decision"] == "retrain"


def test_too_few_rows_is_insufficient():
    assert compute(make(2000), make(20))["decision"] == "insufficient_data"
