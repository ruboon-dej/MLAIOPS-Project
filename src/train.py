"""
make train

Trains the RandomForest forecaster and compares it against the persistence
baseline (predict next hour = current occupancy). Logs params, metrics, and
the model artifact to local MLflow (sqlite backend, artifact root from
BLOB_URI if set, else local data/mlruns/).

Per architecture.md section 5: the SQLite registry only exists on this
machine. After training, this script also writes data/models/latest/ as a
plain artifact directory, which is what score.py actually loads via
MODEL_URI — this sidesteps the "job can't resolve models:/ name" problem.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.insert(0, str(Path(__file__).parent))
from features import build_features, persistence_baseline, TARGET  # noqa: E402

DATA_PATH = os.environ.get("DATA_PATH", "data/ed_timeseries.csv")
MODEL_OUT = Path(os.environ.get("MODEL_URI", "data/models/latest"))


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "no-git"


def dvc_data_hash(path: str) -> str:
    """Cheap stand-in for a DVC hash when DVC isn't initialized yet: a file
    content hash. Once DVC is set up, swap this for `dvc get` / .dvc hash."""
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:12]


def metrics_for(y_true, y_pred) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def main():
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    mlflow.set_experiment("ed_occupancy_1h")

    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # chronological 80/10/10 split — never shuffle time series
    n = len(df)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)
    train_df, val_df, test_df = df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]

    X_train, y_train = build_features(train_df), train_df[TARGET]
    X_test, y_test = build_features(test_df), test_df[TARGET]

    with mlflow.start_run() as run:
        model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        pred = model.predict(X_test)
        model_metrics = metrics_for(y_test, pred)

        baseline_pred = persistence_baseline(test_df)
        baseline_metrics = metrics_for(y_test, baseline_pred)

        mlflow.log_params({
            "n_estimators": 200, "max_depth": 12,
            "train_rows": len(train_df), "test_rows": len(test_df),
            "data_hash": dvc_data_hash(DATA_PATH),
            "git_commit": git_commit(),
        })
        for k, v in model_metrics.items():
            mlflow.log_metric(f"model_{k}", v)
        for k, v in baseline_metrics.items():
            mlflow.log_metric(f"baseline_{k}", v)

        # pickle, not the skops default: skops refuses to serialize
        # RandomForest's internal tree structure as "untrusted". Pickle is
        # the right call here because we trust our own training output —
        # this is NOT safe for loading models from an untrusted source.
        mlflow.sklearn.log_model(model, "model", serialization_format="pickle")

        # Write the plain-artifact copy score.py actually loads. Must be
        # idempotent — CI runs `make train` on every push, and
        # mlflow.sklearn.save_model refuses to write into a non-empty dir.
        import shutil
        sklearn_model_dir = MODEL_OUT / "sklearn_model"
        if sklearn_model_dir.exists():
            shutil.rmtree(sklearn_model_dir)
        MODEL_OUT.mkdir(parents=True, exist_ok=True)
        mlflow.sklearn.save_model(
            model, str(sklearn_model_dir), serialization_format="pickle"
        )

        lineage = {
            "mlflow_run_id": run.info.run_id,
            "git_commit": git_commit(),
            "data_hash": dvc_data_hash(DATA_PATH),
            "model_metrics": model_metrics,
            "baseline_metrics": baseline_metrics,
            "beats_baseline": model_metrics["mae"] < baseline_metrics["mae"],
        }
        with open(MODEL_OUT / "lineage.json", "w") as f:
            json.dump(lineage, f, indent=2)

        print(json.dumps(lineage, indent=2))
        print(f"\nModel artifact + lineage written to {MODEL_OUT}/")
        print(f"MLflow run: {run.info.run_id} (tracking_uri={mlflow.get_tracking_uri()})")
        print(
            "IMPORTANT (architecture.md section 5): record this run_id in the repo "
            "(e.g. docs/MODELS.md) so teammates don't each end up with a different "
            "local registry."
        )


if __name__ == "__main__":
    main()
