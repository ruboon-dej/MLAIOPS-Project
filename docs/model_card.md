# Model Card — ED Occupancy Forecaster

**Model:** RandomForestRegressor, 1-hour-ahead ED occupancy
**Version:** run `6975ce4aba17459fa68fcc3e7022b44c` (fill in your own after retraining)
**Date trained:** [fill in]
**Owners:** Suppavich Rattanamanotham (modeling), Phatpharid Phattaranawig (data pipeline)

## Intended use
Gives charge nurses and bed managers a 1-hour-ahead occupancy estimate, refreshed
hourly, to support short-term staffing and bed decisions. **Not** a clinical tool,
not a replacement for staff judgement, not validated on real patient data.

## Training data
Simulated hourly ED dataset, 4,315 rows, 2025-01-01 to 2025-06-29. No real patient
data. Features: current occupancy, arrivals/departures (1h/3h/6h), triage-level
counts, complaint-category counts, length-of-stay stats, calendar features
(hour-of-day via cyclical encoding, day-of-week, weekend flag). Chronological
80/10/10 train/val/test split — never shuffled, since this is time-series data.

## Performance (test set, n=432)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **RandomForest (this model)** | **2.45** | **3.17** | **0.81** |
| Persistence baseline (predict = current occupancy) | 2.79 | 3.54 | 0.76 |

The model beats the naive baseline on every metric, but the margin is modest —
about 12% lower MAE. This is expected for a 1-hour-ahead horizon where recent
occupancy is already highly predictive. **Accuracy carries no marks in this
course**; this table exists for honesty, not to claim a breakthrough.

## Limitations
- Trained on simulated, not real, hospital data — patterns may not transfer.
- Degrades silently beyond the training distribution (e.g. a mass-casualty
  event, a pandemic surge) since nothing in the features represents rare events.
- Degraded-freshness predictions (1–2h-old data) are published anyway, flagged;
  users should weight these lower than normal predictions.
- No fairness/bias analysis performed — the dataset has no demographic fields, so
  none is possible, but this is a genuine gap if the data source ever changes.

## Monitoring in production
- Freshness: see architecture.md "Freshness states" table.
- `ed_data_age_minutes`, `ed_forecast_state`, `ed_scoring_latency_seconds`,
  `ed_predicted_occupancy` emitted to Cloud Monitoring per scoring run.
- Alert: data age over 120 minutes triggers an email to the team.

## Reproducing this model
```bash
make validate
make train
```
Lineage (run ID, git commit, data hash) is written to `data/models/latest/lineage.json`.
