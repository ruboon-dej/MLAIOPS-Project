# Model registry log

Since MLflow's SQLite backend only exists on the machine that trained
(architecture.md section 5), this file is the team's shared source of truth
for which run is "the" current model. **Only the person in "Owner" below
trains and promotes models** — everyone else reads this file.

**Current owner of training/registration: Suppavich Rattanamanotham**

| Date | MLflow run ID | Git commit | Data hash | Model MAE | Beats baseline? | Promoted to MODEL_URI? |
|---|---|---|---|---|---|---|
| 2026-10-05 | `2ba7a0d1e62f4da6867ef0dcd6b7a93d` | `fe0c1c4` | `7ea3ae080dab` | 2.45 | yes | [ ] |

Note: the deploy job in CI retrains from the same code, data and seed (random_state=42), so the deployed model has the same metrics but a different run ID. The official reference run is the one in the table above.
