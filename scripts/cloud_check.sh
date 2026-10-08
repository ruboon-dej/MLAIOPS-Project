#!/usr/bin/env bash
: "${PROJECT_ID:?set PROJECT_ID}"; : "${REGION:?set REGION}"
BUCKET="${BUCKET:-gs://${PROJECT_ID}-ed-forecaster}"; REPO_NAME="${REPO_NAME:-ed-forecaster}"
fail=0
check() { if "${@:2}" >/dev/null 2>&1; then echo "OK       $1"; else echo "MISSING  $1"; fail=1; fi; }
for sa in runtime invoker deployer; do
  check "service account ed-forecaster-$sa" gcloud iam service-accounts describe "ed-forecaster-$sa@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID"
done
check "bucket $BUCKET" gcloud storage buckets describe "$BUCKET"
check "artifact repo $REPO_NAME" gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID"
check "cloud run job ed-occupancy-scorer" gcloud run jobs describe ed-occupancy-scorer --region="$REGION" --project="$PROJECT_ID"
check "scheduler job ed-occupancy-hourly" gcloud scheduler jobs describe ed-occupancy-hourly --location="$REGION" --project="$PROJECT_ID"
exit $fail
