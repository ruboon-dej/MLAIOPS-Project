# Scoring job image — run as a Cloud Run Job, triggered by Cloud Scheduler.
# Keep this minimal: image size directly affects cold-start time
# (architecture.md section 9, "Cold start is a number to produce").
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# --no-cache-dir and excluding dev-only deps (pytest) keeps the image lean.
RUN pip install --no-cache-dir \
    pandas numpy scikit-learn mlflow google-cloud-storage google-cloud-monitoring

COPY src/ src/
COPY cloudlayer/ cloudlayer/
COPY data/models/latest/ data/models/latest/

ENV CLOUD_PROVIDER=gcp

ENTRYPOINT ["python3", "src/score.py"]
