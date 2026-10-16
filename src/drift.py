import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

PSI_WARN = 0.1
PSI_DRIFT = 0.25
KS_ALPHA = 0.01
RETRAIN_SHARE = 0.3
MIN_ROWS = 100
REFERENCE_FRACTION = 0.8


def psi(reference, current, bins=10):
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    r = np.histogram(reference, edges)[0] / len(reference)
    c = np.histogram(current, edges)[0] / len(current)
    r = np.clip(r, 1e-4, None)
    c = np.clip(c, 1e-4, None)
    return float(np.sum((c - r) * np.log(c / r)))


def compute(reference, current):
    if len(current) < MIN_ROWS:
        return {"decision": "insufficient_data", "rows_current": int(len(current)), "features": []}
    columns = [c for c in reference.select_dtypes("number").columns if c in current.columns]
    features = []
    for col in columns:
        r = reference[col].dropna().to_numpy()
        u = current[col].dropna().to_numpy()
        if len(r) == 0 or len(u) == 0:
            continue
        value = psi(r, u)
        p = float(ks_2samp(r, u).pvalue)
        if value >= PSI_DRIFT and p < KS_ALPHA:
            status = "drift"
        elif value >= PSI_WARN:
            status = "warn"
        else:
            status = "ok"
        features.append({"feature": col, "psi": round(value, 4), "ks_p": round(p, 6), "status": status})
    drifted = [f for f in features if f["status"] == "drift"]
    warned = [f for f in features if f["status"] == "warn"]
    share = len(drifted) / len(features) if features else 0.0
    if share >= RETRAIN_SHARE:
        decision = "retrain"
    elif drifted or warned:
        decision = "monitor"
    else:
        decision = "ok"
    return {
        "decision": decision,
        "rows_current": int(len(current)),
        "drift_share": round(share, 3),
        "features": sorted(features, key=lambda f: -f["psi"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", default="data/ed_timeseries.csv")
    parser.add_argument("--current", required=True)
    parser.add_argument("--window-rows", type=int, default=500)
    parser.add_argument("--out", default="data/reports/drift.json")
    parser.add_argument("--fail-on-retrain", action="store_true")
    args = parser.parse_args()

    full = pd.read_csv(args.reference)
    reference = full.iloc[: int(len(full) * REFERENCE_FRACTION)]
    current = pd.read_csv(args.current).tail(args.window_rows)

    report = compute(reference, current)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2))

    print(f"decision: {report['decision']}  rows: {report['rows_current']}  drift_share: {report.get('drift_share', 0)}")
    for f in report["features"][:5]:
        print(f"  {f['feature']:<30} psi={f['psi']:<8} ks_p={f['ks_p']:<10} {f['status']}")

    if args.fail_on_retrain and report["decision"] == "retrain":
        sys.exit(2)


if __name__ == "__main__":
    main()
