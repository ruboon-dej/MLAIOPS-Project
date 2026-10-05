"""
make replay

The dataset is static and ends 2025-06-29, so "data one hour old" only means
something because this process emits one historical row per real hour,
re-timestamped to now. (architecture.md section 9, "Replay clock".)

Writes to data/live/latest.csv, overwriting each time, so score.py always
reads the most recent emitted row plus history.

--fast lets you compress "one hour" into a few real seconds, for the
presentation demo, where you don't want to wait an hour live.

Stopping this process (Ctrl+C or killing it) IS failure demonstration 1:
the feed goes stale, and the freshness guard in score.py should catch it.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from cloudlayer import get_adapter  # noqa: E402

SOURCE = Path("data/ed_timeseries.csv")
LIVE_DIR = Path("data/live")
LIVE_FILE = LIVE_DIR / "latest.csv"
HISTORY_FILE = LIVE_DIR / "history.csv"


def main():
    parser = argparse.ArgumentParser(description="Replay the ED dataset as a live hourly feed.")
    parser.add_argument(
        "--interval-seconds", type=float, default=3600.0,
        help="Real seconds between emitted rows. Default 3600 (one real hour). "
             "Use a small number (e.g. 5) for a live demo.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Stop after emitting this many rows (useful for demos/tests).",
    )
    args = parser.parse_args()

    df = pd.read_csv(SOURCE, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    LIVE_DIR.mkdir(parents=True, exist_ok=True)

    adapter = get_adapter()
    history_rows = []
    emitted = 0

    print(f"Replay starting: {len(df)} historical rows, interval={args.interval_seconds}s", file=sys.stderr)

    for _, row in df.iterrows():
        row = row.copy()
        # Re-timestamp to "now" so the freshness guard sees a genuinely
        # recent row, while keeping every other column (including
        # hour_of_day / day_of_week) exactly as the historical data had it —
        # that's intentional: we're replaying the pattern, not pretending
        # it's a different time of day.
        row["timestamp"] = datetime.now(timezone.utc).replace(tzinfo=None)

        history_rows.append(row)
        history_df = pd.DataFrame(history_rows)
        history_df.to_csv(HISTORY_FILE, index=False)

        pd.DataFrame([row]).to_csv(LIVE_FILE, index=False)
        # With CLOUD_PROVIDER=gcp this puts the feed where the Cloud Run job can read it.
        # With the local adapter it just copies into data/local_cloud/.
        adapter.upload(str(LIVE_FILE), "live/latest.csv")
        adapter.upload(str(HISTORY_FILE), "live/history.csv")

        emitted += 1
        print(
            f"[{row['timestamp'].isoformat()}] emitted row {emitted}/{len(df)} "
            f"(occupancy={row['occupancy']})",
            file=sys.stderr,
        )

        if args.limit and emitted >= args.limit:
            break

        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
