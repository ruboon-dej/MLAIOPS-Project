# Model registry log

Since MLflow's SQLite backend only exists on the machine that trained
(architecture.md section 5), this file is the team's shared source of truth
for which run is "the" current model. **Only the person in "Owner" below
trains and promotes models** — everyone else reads this file.

**Current owner of training/registration: Suppavich Rattanamanotham**

| Date | MLflow run ID | Git commit | Data hash | Model MAE | Beats baseline? | Promoted to MODEL_URI? |
|---|---|---|---|---|---|---|
| 2026-10-05 | `12c99969d67140c1ad7d3ec1d11b522f` | `2a7db16` | `7ea3ae080dab` | 2.45 | yes | [ ] |
