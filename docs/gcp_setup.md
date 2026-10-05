# GCP setup runbook

Run these yourself, in order, from a machine with `gcloud` installed and
authenticated (`gcloud auth login`) against your course GCP project. Replace
`PROJECT_ID`, `STUDENT_ID`, and `REGION` throughout.

## 0. Variables

```bash
export PROJECT_ID="your-project-id"
export REGION="asia-southeast1"
export STUDENT_ID="6688022"
export BUCKET="gs://${PROJECT_ID}-ed-forecaster"
export REPO_NAME="ed-forecaster"
gcloud config set project "$PROJECT_ID"
```

## 1. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudbilling.googleapis.com
```

## 2. Create the three service accounts (architecture.md section 4)

```bash
gcloud iam service-accounts create ed-forecaster-runtime \
  --display-name="ED forecaster: runtime identity"
gcloud iam service-accounts create ed-forecaster-invoker \
  --display-name="ED forecaster: Scheduler invoker identity"
gcloud iam service-accounts create ed-forecaster-deployer \
  --display-name="ED forecaster: CI deployer identity"

export RUNTIME_SA="ed-forecaster-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
export INVOKER_SA="ed-forecaster-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
export DEPLOYER_SA="ed-forecaster-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
```

## 3. Create the bucket and Artifact Registry repo

```bash
gcloud storage buckets create "$BUCKET" \
  --location="$REGION" \
  --uniform-bucket-level-access

gcloud artifacts repositories create "$REPO_NAME" \
  --repository-format=docker \
  --location="$REGION"
```

## 4. Grant roles (narrowest scope — matches architecture.md's permissions table)

```bash
# Runtime: reads bucket + model artifact, writes metrics/logs, pulls image
gcloud storage buckets add-iam-policy-binding "$BUCKET" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/storage.objectAdmin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/monitoring.metricWriter"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/logging.logWriter"
gcloud artifacts repositories add-iam-policy-binding "$REPO_NAME" \
  --location="$REGION" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/artifactregistry.reader"

# Invoker: only allowed to invoke THIS job, not project-wide
# (grant after the job is created — see step 6)

# Deployer: pushes images, updates the job, and must be able to actAs runtime
gcloud artifacts repositories add-iam-policy-binding "$REPO_NAME" \
  --location="$REGION" \
  --member="serviceAccount:${DEPLOYER_SA}" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" --role="roles/run.developer"
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:${DEPLOYER_SA}" --role="roles/iam.serviceAccountUser"
# ^ This is the one most likely to be missed and cause the first deploy to
# fail (architecture.md section 4). Updating a job that runs as another
# account counts as acting as it.
```

## 5. Workload Identity Federation for GitHub Actions (no key files)

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" --display-name="GitHub Actions pool"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Restrict to YOUR repo only
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/ruboon-dej/MLAIOPS-Project"
```

Then, in your GitHub repo settings → Secrets and variables → Actions, set:
- **Secret** `WIF_PROVIDER`: output of `gcloud iam workload-identity-pools providers describe github-provider --location=global --workload-identity-pool=github-pool --format='value(name)'`
- **Secret** `DEPLOYER_SA`: `$DEPLOYER_SA`
- **Variable** `PROJECT_ID`, **Variable** `REGION`

## 6. Create the Cloud Run Job (first deploy — after CI/CD pushes an image)

```bash
gcloud run jobs create ed-occupancy-scorer \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/scorer:latest" \
  --region="$REGION" \
  --service-account="$RUNTIME_SA" \
  --set-env-vars="CLOUD_PROVIDER=gcp,PROJECT_ID=${PROJECT_ID},BLOB_URI=${BUCKET},FRESH_OK_MINUTES=60,FRESH_STALE_MINUTES=120,SCORE_DEADLINE_MINUTES=5,METRICS_NAMESPACE=itcs355" \
  --labels="course=itcs355,student=${STUDENT_ID},lab=capstone" \
  --max-retries=0 \
  --task-timeout=300

# Now grant the invoker account permission on THIS job specifically
gcloud run jobs add-iam-policy-binding ed-occupancy-scorer \
  --region="$REGION" \
  --member="serviceAccount:${INVOKER_SA}" \
  --role="roles/run.invoker"
```

## 7. Create the Cloud Scheduler job

```bash
# Cloud Run Jobs use --oauth-service-account-email, NOT an OIDC token
# (OIDC is for Cloud Run services, not jobs — architecture.md section 4).
gcloud scheduler jobs create http ed-occupancy-hourly \
  --location="$REGION" \
  --schedule="5 * * * *" \
  --time-zone="UTC" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/ed-occupancy-scorer:run" \
  --http-method=POST \
  --oauth-service-account-email="$INVOKER_SA"
```

## 8. Billing budget alert

```bash
# Requires a billing account ID — find it with:
gcloud billing accounts list

gcloud billing budgets create \
  --billing-account="YOUR_BILLING_ACCOUNT_ID" \
  --display-name="itcs355-ed-forecaster" \
  --budget-amount=800THB \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.8 \
  --threshold-rule=percent=1.0
```
Then set up the notification channel (email) in the Cloud Console — this
isn't fully scriptable without a Pub/Sub topic, and the course likely just
wants the budget object to exist with the right thresholds.

## 9. Monitoring dashboard + alert

Simplest path: Cloud Monitoring → Dashboards → create from the
`ed_data_age_minutes` and `ed_forecast_state` custom metrics (these appear
automatically after the first real `emit_metric` call from the GCP adapter).
Alert policy: `ed_data_age_minutes > 120` for any value → email the team.

## 10. Verify, then run the pipeline

```bash
make cloud-check     # once you've written it to check the above exists
gcloud run jobs execute ed-occupancy-scorer --region="$REGION"   # manual test run
```

## 11. Before submission: cost report, then teardown

```bash
make cost-report
gcloud scheduler jobs delete ed-occupancy-hourly --location="$REGION" --quiet
gcloud run jobs delete ed-occupancy-scorer --region="$REGION" --quiet
gcloud storage rm -r "$BUCKET"
gcloud artifacts repositories delete "$REPO_NAME" --location="$REGION" --quiet
```
Double-check the Cloud Console billing page shows no resources with the
`student=${STUDENT_ID}` label still running — this is where the automatic
deduction for "resources left running" gets triggered.
