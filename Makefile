.PHONY: setup validate train test audit-src replay score failure-demo \
        cloud-check teardown cost-report portability-audit clean

# cloud.env is gitignored (it holds project-specific, non-secret config and
# would hold secrets if any crept in) so it may not exist yet — create it
# from the example on first run rather than failing.
ifeq (,$(wildcard cloud.env))
$(shell cp cloud.env.example cloud.env)
endif
include cloud.env
export

setup:
	python3 -m venv .venv || true
	. .venv/bin/activate && pip install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt

validate:
	python3 src/validate.py data/ed_timeseries.csv

train: validate
	python3 src/train.py

test:
	python3 -m pytest tests/ -v

audit-src:
	@echo "Checking src/ for hardcoded cloud references..."
	@! grep -rniE "s3://|abfss://|gs://|amazonaws|azure|googleapis" src/ && echo "PASS: no hardcoded cloud references in src/"

replay:
	python3 src/replay.py

replay-fast:
	python3 src/replay.py --interval-seconds 5

score:
	python3 src/score.py

failure-demo:
	bash scripts/failure_demo.sh

# --- GCP-side targets: require cloud.env to be filled in and gcloud auth ---

cloud-check:
	@bash scripts/cloud_check.sh

teardown:
	@bash scripts/teardown.sh

cost-report:
	@echo "cost-report: pulls billing data filtered by project labels"
	@echo "Not implemented in this sandbox. See docs/gcp_setup.md."

portability-audit:
	@echo "portability-audit: course-provided target, copy in from course repo"

clean:
	rm -rf data/live data/local_cloud data/reports mlflow.db .pytest_cache
