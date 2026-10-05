"""
GCP CloudAdapter. The only module in this repo that imports a GCP SDK
(per architecture.md section 1, Layer 3). Selected when CLOUD_PROVIDER=gcp.

Authenticates via Application Default Credentials: the runtime service
account when running on Cloud Run, or `gcloud auth application-default
login` on a laptop (see architecture.md section 1).
"""
from __future__ import annotations

import os
import subprocess

from .base import CloudAdapter


class GCPAdapter(CloudAdapter):
    def __init__(self):
        # Imports are inside __init__, not at module level, so that
        # `import cloudlayer.gcp` doesn't require the google-cloud packages
        # to be installed unless this adapter is actually selected.
        from google.cloud import storage
        from google.cloud import monitoring_v3

        self.bucket_uri = os.environ["BLOB_URI"]  # e.g. gs://my-bucket
        self.bucket_name = self.bucket_uri.replace("gs://", "").split("/")[0]
        self.project_id = os.environ["PROJECT_ID"]
        self.metrics_namespace = os.environ.get("METRICS_NAMESPACE", "itcs355")

        self.storage_client = storage.Client(project=self.project_id)
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.monitoring_client = monitoring_v3.MetricServiceClient()

    def upload(self, local_path: str, remote_path: str) -> None:
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(local_path)

    def download(self, remote_path: str, local_path: str) -> None:
        blob = self.bucket.blob(remote_path)
        blob.download_to_filename(local_path)

    def push_image(self, local_tag: str, remote_tag: str) -> None:
        # CI calls `docker push` directly in most setups; this wrapper exists
        # so score.py / train.py never need to know whether they're calling
        # docker or something else.
        subprocess.run(["docker", "tag", local_tag, remote_tag], check=True)
        subprocess.run(["docker", "push", remote_tag], check=True)

    def emit_metric(self, name: str, value: float, labels: dict[str, str]) -> None:
        from google.cloud import monitoring_v3
        import time

        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/{self.metrics_namespace}/{name}"
        series.resource.type = "global"
        series.resource.labels["project_id"] = self.project_id
        for k, v in labels.items():
            series.metric.labels[k] = str(v)

        now = time.time()
        point = monitoring_v3.Point(
            {
                "interval": {"end_time": {"seconds": int(now)}},
                "value": {"double_value": value},
            }
        )
        series.points = [point]
        self.monitoring_client.create_time_series(
            name=f"projects/{self.project_id}", time_series=[series]
        )

    def teardown(self, labels: dict[str, str]) -> None:
        # Deliberately NOT implemented as a blind delete-everything — that's
        # a disaster waiting to happen. `make teardown` should shell out to
        # gcloud commands filtered by the project labels (see
        # architecture.md section 6), reviewed by a human before running.
        raise NotImplementedError(
            "teardown is done via `make teardown` (gcloud CLI, label-filtered), "
            "not via this Python method — see architecture.md section 6"
        )
