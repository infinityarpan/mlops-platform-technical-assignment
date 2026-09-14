from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.domain.enums import LifecycleStage  # noqa: E402
from app.models.entities import Base, Deployment, DeploymentEvent  # noqa: E402
from app.schemas import ModelCreate, VersionCreate  # noqa: E402
from app.services.evidently_drift import publish_drift_scores  # noqa: E402
from app.services.inference_metrics import record_operational_sample  # noqa: E402
from app.services.metrics_push import push_inference_metrics  # noqa: E402
from app.services.mlflow_registry import MLflowRegistry  # noqa: E402

DATA = ROOT / "data"

VALVE = {
    "model_id": "valve-health-model",
    "name": "Valve Health Model",
    "owner": "Reliability AI Team",
    "framework": "xgboost",
    "versions": [
        {"version": "1.0.0", "stage": "Archived", "artifact_uri": "s3://models/valve/1.0.0"},
        {"version": "2.0.0", "stage": "Staging", "artifact_uri": "s3://models/valve/2.0.0"},
        {"version": "3.0.0", "stage": "None", "artifact_uri": "s3://models/valve/3.0.0"},
    ],
}


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def wait_for_pushgateway(timeout_seconds: float = 60.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = httpx.get(f"{settings.pushgateway_url}/-/ready", timeout=2.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    raise RuntimeError(f"Pushgateway not ready at {settings.pushgateway_url}")


def seed_prometheus_metrics() -> None:
    wait_for_pushgateway()
    with (DATA / "sample_model_metrics.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: parse_ts(row["timestamp"]))

    seen_models: set[str] = set()
    for row in rows:
        record_operational_sample(
            model_id=row["model_id"],
            version=row["version"],
            environment=row["environment"],
            latency_ms=float(row["latency_ms"]),
            throughput_rpm=float(row["throughput_rpm"]),
            error_rate=float(row["error_rate"]),
            quality_score=float(row["quality_score"]),
            availability=float(row["availability"]),
        )
        push_inference_metrics()
        seen_models.add(row["model_id"])
        time.sleep(settings.metrics_seed_interval_seconds)

    for model_id in sorted(seen_models):
        production_version = next(
            (row["version"] for row in reversed(rows) if row["model_id"] == model_id),
            "1.0.0",
        )
        publish_drift_scores(
            model_id=model_id,
            version=production_version,
            environment="production",
        )
        push_inference_metrics()

    time.sleep(5)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    registry = MLflowRegistry()
    try:
        if db.scalar(select(Deployment).limit(1)):
            print("Database already seeded")
            return
        if registry.list_models():
            print("MLflow registry already seeded")
            return

        registry_items = json.loads((DATA / "sample_model_registry.json").read_text(encoding="utf-8"))
        registry_items.append(VALVE)
        versions_by_key: dict[tuple[str, str], str] = {}

        for item in registry_items:
            registry.create_model(
                ModelCreate(
                    id=item["model_id"],
                    name=item["name"],
                    owner=item["owner"],
                    description=f"Seeded industrial model ({item.get('framework', 'unknown')}).",
                )
            )
            for ver in item["versions"]:
                version = registry.register_version(
                    item["model_id"],
                    VersionCreate(
                        version=ver["version"],
                        framework=item.get("framework"),
                        artifact_uri=ver["artifact_uri"],
                        training_data_ref=f"s3://training/{item['model_id']}/{ver['version']}",
                        tags=["industrial", "seed"],
                        extra_metadata={"source": "assignment-artifacts"},
                    ),
                )
                stage = LifecycleStage(ver["stage"])
                if stage != LifecycleStage.NONE:
                    registry.transition_stage(item["model_id"], ver["version"], stage)
                versions_by_key[(item["model_id"], ver["version"])] = version.id

        events = json.loads((DATA / "sample_deployment_events.json").read_text(encoding="utf-8"))
        for event in events:
            version_id = versions_by_key.get((event["model_id"], event["version"]))
            if version_id is None:
                continue
            deployment = Deployment(
                id=event["deployment_id"],
                model_id=event["model_id"],
                version_id=version_id,
                version=event["version"],
                environment=event["environment"],
                status=event["status"],
                failure_class=event["event"] if event["status"] == "FAILED" else None,
                failure_reason=event["event"] if event["status"] == "FAILED" else None,
                created_at=parse_ts(event["timestamp"]),
            )
            db.add(deployment)
            db.flush()
            db.add(
                DeploymentEvent(
                    deployment_id=deployment.id,
                    event=event["event"],
                    status=event["status"],
                    message=event["event"],
                    created_at=parse_ts(event["timestamp"]),
                )
            )

        db.commit()
        seed_prometheus_metrics()
        print(
            "Seed complete "
            f"(MLflow: {settings.mlflow_tracking_uri}, Pushgateway: {settings.pushgateway_url})"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
