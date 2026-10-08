"""Capstone cost report: batch-job adaptation of the Lab 5 scaffold.

    python scripts/cost_report.py --estimate 150 --actual 42 --days 14 \
        --storage 6 --serving 0 --pipeline 0 --monitoring 0 --other 36

Writes reports/cost-report.md with the six sections Lab 5 Task 5 requires.
All figures are THB, typed in from Billing (Reports, filtered to the project
and grouped by service). This script does not call any billing API.

Adaptation note: the lab version prices an always-on endpoint (hourly rate and
req/s). This project is an hourly batch job with one prediction per run, so
"utilisation" here means the share of the 720 scheduled hourly runs that
actually produce a prediction. Fixed costs stay constant across the rows.
"""
from __future__ import annotations

import argparse
from pathlib import Path

UTILISATIONS = (0.05, 0.25, 0.80, 1.00)


def per_1k(monthly_thb: float, runs_per_month: int, utilisation: float) -> float:
    predictions = runs_per_month * utilisation
    return monthly_thb / (predictions / 1000) if predictions else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", type=float, required=True, help="THB, predicted in advance")
    ap.add_argument("--actual", type=float, required=True, help="THB, from billing, filtered to the project")
    ap.add_argument("--days", type=float, required=True, help="days of billing the actual figure covers")
    ap.add_argument("--runs-per-month", type=int, default=720)
    ap.add_argument("--storage", type=float, default=0.0, help="Cloud Storage + Artifact Registry")
    ap.add_argument("--serving", type=float, default=0.0, help="Cloud Run Jobs")
    ap.add_argument("--pipeline", type=float, default=0.0, help="Scheduler, CI related")
    ap.add_argument("--monitoring", type=float, default=0.0, help="Cloud Monitoring + Logging")
    ap.add_argument("--other", type=float, default=0.0)
    ap.add_argument("--out", type=Path, default=Path("reports/cost-report.md"))
    args = ap.parse_args()

    gap = args.actual - args.estimate
    gap_pct = (gap / args.estimate * 100) if args.estimate else float("nan")
    monthly = args.actual / args.days * 30 if args.days else float("nan")
    parts = args.storage + args.serving + args.pipeline + args.monitoring + args.other

    rows = "\n".join(
        f"| {int(u * 100)}% | {args.runs_per_month * u:.0f} | {per_1k(monthly, args.runs_per_month, u):.2f} |"
        for u in UTILISATIONS
    )

    content = f"""# Cost report (capstone, hourly batch job)

Project `itcs355-edforecast` · region `asia-southeast1` · {args.runs_per_month} scheduled runs per month

## 1. Estimate, made before running
{args.estimate:.2f} THB

## 2. Actual, from billing filtered to the project
{args.actual:.2f} THB over {args.days:g} days (about {monthly:.2f} THB projected per 30 days)

## 3. The gap
{gap:+.2f} THB ({gap_pct:+.1f}%)

TODO: explain it in your own words. Name real causes from this project, for example
test runs and failure demos that ran outside the hourly schedule, storage left in the
bucket, or a service you left out of the estimate.

## 4. Breakdown by component
| Component | THB | Notes |
|---|---|---|
| Training | 0.00 | Runs locally and in CI, no cloud training |
| Storage | {args.storage:.2f} | Cloud Storage and Artifact Registry |
| Serving | {args.serving:.2f} | Cloud Run Jobs |
| Pipeline | {args.pipeline:.2f} | Cloud Scheduler |
| Monitoring | {args.monitoring:.2f} | Cloud Monitoring and Logging |
| Other | {args.other:.2f} | |
| **Sum of rows** | **{parts:.2f}** | Actual from billing: {args.actual:.2f} |

TODO: if the sum differs from the actual, say why (credits, rounding, a service not listed).

## 5. Cost per 1,000 predictions
One prediction per run. Utilisation is the share of scheduled hourly runs that score
(the rest are refusals or skipped). Cost is the projected monthly figure above.

| Utilisation | Predictions per month | THB per 1,000 |
|---|---|---|
{rows}

State which row you believe, and why. The design target is 100%.

## 6. One optimisation you applied
| | Before | After |
|---|---|---|
| Configuration | | |
| THB per 1,000 | | |
| Run time or latency | | |

TODO: apply one real change, then fill this with measured before and after figures.
Report the latency cost too.
"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(content)
    print(f"wrote {args.out}")
    print(f"gap {gap:+.2f} THB ({gap_pct:+.1f}%)")
    if abs(gap_pct) > 20:
        print("Gap exceeds 20%. The lab requires your figure to match billing within 20%.")
    if abs(parts - args.actual) > 0.01:
        print(f"Component rows sum to {parts:.2f}, not {args.actual:.2f}. Explain the difference in section 4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
