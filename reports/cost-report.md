# Cost report (capstone, hourly batch job)

Project `itcs355-edforecast` · region `asia-southeast1` · 720 scheduled runs per month

## 1. Estimate, made before running
13.30 THB

## 2. Actual, from billing filtered to the project
0.27 THB over 4 days (about 2.03 THB projected per 30 days)

## 3. The gap
-13.03 THB (-98.0%)

The actual cost came in 98% below the estimate (0.27 THB against 13.30 THB for the
same 4-day window, prorated from a proposal range of about $1-5 per month). The
estimate was deliberately conservative and assumed small but non-zero charges from
every service. In practice Cloud Run Jobs and Cloud Scheduler stayed inside their
free tiers, and Cloud Storage and Artifact Registry billed 0.00 THB at this data
size. All 0.27 THB came from Cloud Run, and it appears only on 5, 6 and 7 October,
so it likely reflects setup, test runs and failure demos rather than the steady
hourly schedule. Caveats: only 4 days of billing exist, so the monthly projection
(about 2.03 THB) is rough, and these figures are before the free trial credit, which
covered them (net bill 0.00 THB). Without the credit the cost would be about
2.03 THB per month, still below the low end of the proposal range.

## 4. Breakdown by component
| Component | THB | Notes |
|---|---|---|
| Training | 0.00 | Runs locally and in CI, no cloud training |
| Storage | 0.00 | Cloud Storage and Artifact Registry |
| Serving | 0.27 | Cloud Run Jobs |
| Pipeline | 0.00 | Cloud Scheduler |
| Monitoring | 0.00 | Cloud Monitoring and Logging |
| Other | 0.00 | |
| **Sum of rows** | **0.27** | Actual from billing: 0.27 |

Rows sum to the billed actual.

## 5. Cost per 1,000 predictions
One prediction per run. Utilisation is the share of scheduled hourly runs that score
(the rest are refusals or skipped). Cost is the projected monthly figure above.

| Utilisation | Predictions per month | THB per 1,000 |
|---|---|---|
| 5% | 36 | 56.25 |
| 25% | 180 | 11.25 |
| 80% | 576 | 3.52 |
| 100% | 720 | 2.81 |

Believed row: 80% (576 predictions per month, 3.52 THB per 1,000). The design target is 100%, but the scorer refuses by design when the feed is more than 120 minutes old, and that refusal was observed on 8 October (data age 122.1 minutes), so some scheduled runs will not score. Of the six recorded executions on 8 October, five scored and one refused (83%), but only one of the six was started by the scheduler and the schedule is currently paused, so steady-state utilisation has not been measured. The 80% row is a judgement, not a measurement. The monthly cost behind every row is projected from 4 days of billing that include setup and test runs.

## 6. One optimisation you applied
| | Before | After |
|---|---|---|
| Configuration | 1 vCPU, 2 GiB, 300 s timeout | 1 vCPU, 1 GiB, 300 s timeout |
| THB per 1,000 | 29.62 | 24.28 |
| Run time or latency | 33.0 s mean (5 runs) | 29.8 s mean (3 runs) |

Change applied: memory lowered from 2 GiB to 1 GiB with gcloud run jobs update. Run time went from a 33.0 s mean over five runs to 29.8 s over three runs, a change of -3.2 s per run. This is within run-to-run variation (the three runs ranged from 28.4 s to 30.5 s), so no latency cost was measured, and the saving comes from the lower memory charge alone. Cost per 1,000 predictions is modelled from Google's published Tier 2 list rates for jobs in asia-southeast1 (0.0007344 THB per vCPU-second and 0.0000816 THB per GiB-second, converted at 34 THB per USD, one prediction per run) at 29.62 THB before and 24.28 THB after. These list-rate figures are higher than the section 5 table because section 5 is projected from the billed cost, which sits inside the free tier. Compare the before and after columns with each other, not with section 5. All three 1 GiB runs completed without a memory error, and the sample is small.
