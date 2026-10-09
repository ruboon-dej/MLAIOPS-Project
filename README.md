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
  model_card.md, MODELS.md, gcp_setup.md — model card, official run log, GCP runbook
scripts/
  failure_demo.sh             — orchestrates both demos for the live presentation
```

## Cloud deployment (GCP)

Not runnable from this sandbox — these are the commands to run yourself, in order.
See `docs/gcp_setup.md` for the full annotated version with the exact `gcloud` commands.

1. Create the three service accounts and grant the roles table from `architecture.md` §4.
2. Create the bucket, Artifact Registry repo, and set up Workload Identity Federation.
3. Fill in `cloud.env` from `cloud.env.example`.
4. `make cloud-check` — verifies the above before you spend anything.
5. Push to GitHub → GitHub Actions builds the image, runs tests, deploys the Cloud Run Job.
6. Create the Cloud Scheduler job pointing at it.
7. `make cost-report` before submission, then `make teardown`.

Deliberate failure write-up: [docs/failure-mode.md](docs/failure-mode.md)
