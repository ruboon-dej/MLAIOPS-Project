# ED Occupancy Forecaster — ITCS355 Capstone

Hourly batch forecast of emergency department occupancy one hour ahead, deployed on GCP.
See `architecture.md` for the full design. This README covers how to actually run things.

## What exists right now

| Target | Status |
|---|---|
| `make setup`, `make validate`, `make train`, `make test`, `make audit-src` | implemented |
| `make replay`, `make replay-fast`, `make score`, `make failure-demo` | implemented (local/laptop mode) |
| `make cloud-check`, `make teardown`, `make cost-report`, `make portability-audit` | GCP-side, see "Cloud deployment" below |
| GitHub Actions (`.github/workflows/ci-cd.yml`) | deploys to GCP after CI passes on `main` |

## Quickstart (local, no cloud needed)

```bash
make setup          # create venv, install deps
make validate        # run data validation checks against data/ed_timeseries.csv
make train            # train the model, logs to local MLflow (sqlite), writes model artifact
make test              # run pytest — includes the freshness-guard tests
make replay &           # starts emitting one row per real hour into data/live/
make score               # runs one scoring pass against the replay feed
make failure-demo          # runs both deliberate failures and shows the guard catching them
```

## Project layout

```
src/
  validate.py     — schema/leakage/freshness-of-structure checks on raw data
  features.py     — shared feature prep (used by train.py and score.py)
  train.py         — trains RandomForest baseline + persistence baseline, logs to MLflow
  replay.py         — emits one historical row per real hour (or --fast for demo speed)
  freshness.py       — the three-tier freshness guard (normal/degraded/refuse)
  score.py             — one scoring pass: load model, check freshness, predict, write report
cloudlayer/
  base.py            — CloudAdapter interface (11 methods, per architecture.md section 3)
  local.py             — local filesystem implementation (default, no cloud needed)
  gcp.py                — GCS / Artifact Registry / Cloud Run / Monitoring implementation
tests/
  test_validate.py        — validation must reject bad input (failure demo 2)
  test_freshness.py        — guard must refuse stale input (failure demo 1)
docs/
  model_card.md, MODELS.md, gcp_setup.md, failure-mode.md — model card, official run log, GCP runbook, deliberate-failure write-up
scripts/
  failure_demo.sh             — orchestrates both demos for the live presentation
```

## Cloud deployment (GCP)

These are the commands to deploy and operate the system, in order.
See `docs/gcp_setup.md` for the full annotated version with the exact `gcloud` commands.

1. Create the three service accounts and grant the roles table from `architecture.md` §4.
2. Create the bucket, Artifact Registry repo, and set up Workload Identity Federation.
3. Fill in `cloud.env` from `cloud.env.example`.
4. `make cloud-check` — verifies the above before you spend anything.
5. Push to GitHub → GitHub Actions builds the image, runs tests, deploys the Cloud Run Job.
6. Create the Cloud Scheduler job pointing at it.
7. `make cost-report` before submission, then `make teardown`.

Deliberate failure write-up: [docs/failure-mode.md](docs/failure-mode.md)

## Monitoring dashboard

Screenshots of the `ED Forecaster` Cloud Monitoring dashboard, 12 Oct 2026 (UTC+7).

- `docs/dashboard-data-age.png`: data age in minutes. Values above 120 are refused by the guard.
- `docs/dashboard-forecast-state.png`: forecast state, 1 when scored and 0 when refused.

The 122.1 minute stale-data case of 8 Oct 2026 is documented in `docs/failure-mode.md`.

## Drift detection

`src/drift.py` compares the training reference (first 80 percent of `data/ed_timeseries.csv`) with the latest 500 rows. For each numeric column it computes the population stability index (PSI) and a two-sample Kolmogorov-Smirnov test.

- A column is flagged `drift` when PSI is at least 0.25 and the KS p-value is below 0.01, and `warn` when PSI is at least 0.1.
- The decision is `retrain` when at least 30 percent of columns drift, `monitor` when any column warns or drifts, `insufficient_data` below 100 rows, and `ok` otherwise.
- Run it with `make drift CURRENT=<csv>` or the manual `drift` GitHub Actions workflow. With `--fail-on-retrain` the process exits with code 2 when retraining is recommended.

Checked on 16 Oct 2026: the committed data returns `ok` (highest PSI 0.057), and a copy with 19 columns scaled by 1.6 returns `retrain` (drift share 0.667). Thresholds are common defaults and have not been tuned. Small drifts and live cloud data have not been tested. The freshness guard in `docs/failure-mode.md` catches stale data, while this check catches changes in the data distribution.
