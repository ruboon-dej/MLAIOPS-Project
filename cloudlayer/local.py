"""
Local filesystem CloudAdapter. CLOUD_PROVIDER=local (the default) uses this,
so the whole pipeline runs on a laptop with zero GCP setup. Swapping to
CLOUD_PROVIDER=gcp swaps in cloudlayer/gcp.py with no code changes outside
this layer — that's the point of the three-layer rule.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .base import CloudAdapter


class LocalAdapter(CloudAdapter):
    def __init__(self, root: str = "data/local_cloud"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.metrics_log = self.root / "metrics.jsonl"

    def upload(self, local_path: str, remote_path: str) -> None:
        dest = self.root / remote_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(local_path, dest)

    def download(self, remote_path: str, local_path: str) -> None:
        src = self.root / remote_path
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, local_path)

    def push_image(self, local_tag: str, remote_tag: str) -> None:
        print(f"[local adapter] would push image {local_tag} -> {remote_tag} (no-op locally)")

    def emit_metric(self, name: str, value: float, labels: dict[str, str]) -> None:
        import datetime
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metric": name,
            "value": value,
            "labels": labels,
        }
        with open(self.metrics_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def teardown(self, labels: dict[str, str]) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        print(f"[local adapter] teardown complete, removed {self.root}")
