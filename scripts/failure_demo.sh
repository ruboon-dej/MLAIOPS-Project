#!/usr/bin/env bash
# Orchestrates both deliberate failures for the live presentation.
# Run `make train` first so a model artifact exists.
set -uo pipefail

export FRESH_OK_MINUTES=${FRESH_OK_MINUTES:-60}
export FRESH_STALE_MINUTES=${FRESH_STALE_MINUTES:-120}
export SCORE_DEADLINE_MINUTES=${SCORE_DEADLINE_MINUTES:-5}
export MODEL_URI=${MODEL_URI:-data/models/latest}
export CLOUD_PROVIDER=${CLOUD_PROVIDER:-local}

divider() { echo ""; echo "=================================================="; echo "$1"; echo "=================================================="; }

divider "FAILURE DEMO 1: runtime loop — stop the replay feed"
echo "Starting replay feed (fast mode, 2s/row)..."
python3 src/replay.py --interval-seconds 2 --limit 3 > /tmp/replay.log 2>&1
echo "Feed ran for 3 rows then stopped on its own (simulating an outage)."
echo ""
echo "Backdating the live feed by 3 hours, past the ${FRESH_STALE_MINUTES}-minute refuse threshold..."
python3 - <<'EOF'
import pandas as pd
from datetime import datetime, timedelta, timezone
df = pd.read_csv('data/live/latest.csv', parse_dates=['timestamp'])
df['timestamp'] = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
df.to_csv('data/live/latest.csv', index=False)
EOF
echo ""
echo "Running the scorer against the stale feed:"
python3 src/score.py
SCORE_EXIT=$?
if [ $SCORE_EXIT -eq 1 ]; then
    echo ""
    echo "PASS: scorer correctly refused to score stale data (exit code 1)."
else
    echo ""
    echo "UNEXPECTED: scorer should have refused. Exit code was $SCORE_EXIT."
fi
echo ""
echo "Confirming the CI test for this exists and passes:"
python3 -m pytest tests/test_freshness.py::test_data_past_stale_threshold_is_refused -v

divider "FAILURE DEMO 2: build-time loop — bad input blocks deployment"
echo "Corrupting a copy of the dataset (duplicate timestamp)..."
python3 - <<'EOF'
import pandas as pd
df = pd.read_csv('data/ed_timeseries.csv')
df.loc[5, 'timestamp'] = df.loc[4, 'timestamp']
df.to_csv('data/bad_input_demo.csv', index=False)
EOF
echo ""
echo "Running validation against the corrupted file:"
python3 src/validate.py data/bad_input_demo.csv
VALIDATE_EXIT=$?
if [ $VALIDATE_EXIT -eq 1 ]; then
    echo ""
    echo "PASS: validation correctly rejected the bad input (exit code 1)."
    echo "In CI, this exit code blocks the pipeline before training/deployment."
else
    echo ""
    echo "UNEXPECTED: validation should have failed. Exit code was $VALIDATE_EXIT."
fi
echo ""
echo "Confirming the CI test for this exists and passes:"
python3 -m pytest tests/test_validate.py::test_duplicate_timestamps_fail -v
rm -f data/bad_input_demo.csv

divider "Both failure demonstrations complete."
