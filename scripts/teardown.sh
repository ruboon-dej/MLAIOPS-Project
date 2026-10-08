#!/usr/bin/env bash
: "${PROJECT_ID:?set PROJECT_ID}"; : "${REGION:?set REGION}"
BUCKET="${BUCKET:-gs://${PROJECT_ID}-ed-forecaster}"; REPO_NAME="${REPO_NAME:-ed-forecaster}"
if [ "$PROJECT_ID" = "itcs355-6688097" ]; then echo "Refusing: that is the individual lab project."; exit 1; fi
run() { if [ "${DRY_RUN:-0}" = "1" ]; then echo "[dry run] $*"; else "$@" || echo "  (skipped: $*)"; fi; }
if [ "${DRY_RUN:-0}" != "1" ] && [ "${FORCE:-0}" != "1" ]; then
  read -r -p "Delete ed-forecaster resources in $PROJECT_ID? Type the project id to confirm: " ans
  [ "$ans" = "$PROJECT_ID" ] || { echo "Aborted."; exit 1; }
fi
run gcloud scheduler jobs delete ed-occupancy-hourly --location="$REGION" --project="$PROJECT_ID" --quiet
run gcloud run jobs delete ed-occupancy-scorer --region="$REGION" --project="$PROJECT_ID" --quiet
run gcloud storage rm -r "$BUCKET"
run gcloud artifacts repositories delete "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID" --quiet
POL=$(gcloud alpha monitoring policies list --project="$PROJECT_ID" --filter='displayName="ED data stale over 120 min"' --format='value(name)')
[ -n "$POL" ] && run gcloud alpha monitoring policies delete "$POL" --quiet
CH=$(gcloud beta monitoring channels list --project="$PROJECT_ID" --filter='displayName="ED forecaster team email"' --format='value(name)')
[ -n "$CH" ] && run gcloud beta monitoring channels delete "$CH" --quiet
echo "Done. Run 'make cloud-check': the bucket, repo, jobs should say MISSING (service accounts stay, they are free)."
