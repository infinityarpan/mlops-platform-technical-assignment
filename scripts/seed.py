from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db import SessionLocal, engine  # noqa: E402
from app.models.entities import (  # noqa: E402
    Base,
    Deployment,
    DeploymentEvent,
    MetricSample,
    Model,
    ModelVersion,
    new_id,
)

DATA = ROOT / "data"

VALVE = {
    "model_id": "valve-health-model",
    "name": "Valve Health Model",
    "owner": "Reliability AI Team",
    "framework": "xgboost",
    "versions": [
        {"version": "1.0.0", "stage": "ARCHIVED", "approved": True, "artifact_uri": "s3://models/valve/1.0.0"},
        {"version": "2.0.0", "stage": "STAGING", "approved": True, "artifact_uri": "s3://models/valve/2.0.0"},
        {"version": "3.0.0", "stage": "VALIDATED", "approved": True, "artifact_uri": "s3://models/valve/3.0.0"},
    ],
}


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def monitoring_status(error_rate: float, drift_score: float) -> str:
    if error_rate > 0.02 or drift_score > 0.3:
        return "degraded"
    return "healthy"


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Model).limit(1)):
            print("Database already seeded")
            return

        registry = json.loads((DATA / "sample_model_registry.json").read_text(encoding="utf-8"))
        registry.append(VALVE)
        versions_by_key: dict[tuple[str, str], ModelVersion] = {}

        for item in registry:
            model = Model(
                id=item["model_id"],
                name=item["name"],
                owner=item["owner"],
                description=f"Seeded industrial model ({item.get('framework', 'unknown')}).",
            )
            db.add(model)
            db.flush()
            for ver in item["versions"]:
                row = ModelVersion(
                    id=new_id(),
                    model_id=item["model_id"],
                    version=ver["version"],
                    framework=item.get("framework"),
                    algorithm=None,
                    artifact_uri=ver["artifact_uri"],
                    training_data_ref=f"s3://training/{item['model_id']}/{ver['version']}",
                    tags=["industrial", "seed"],
                    extra_metadata={"source": "assignment-artifacts"},
                    approved=ver["approved"],
                    lifecycle_stage=ver["stage"],
                )
                db.add(row)
                db.flush()
                versions_by_key[(item["model_id"], ver["version"])] = row

        events = json.loads((DATA / "sample_deployment_events.json").read_text(encoding="utf-8"))
        for event in events:
            version = versions_by_key.get((event["model_id"], event["version"]))
            if version is None:
                continue
            deployment = Deployment(
                id=event["deployment_id"],
                model_id=event["model_id"],
                version_id=version.id,
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

        with (DATA / "sample_model_metrics.csv").open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                ts = parse_ts(row["timestamp"])
                error_rate = float(row["error_rate"])
                drift = float(row["drift_score"])
                db.add(
                    MetricSample(
                        timestamp=ts,
                        model_id=row["model_id"],
                        version=row["version"],
                        environment=row["environment"],
                        latency_ms=float(row["latency_ms"]),
                        throughput_rpm=float(row["throughput_rpm"]),
                        error_rate=error_rate,
                        quality_score=float(row["quality_score"]),
                        drift_score=drift,
                        availability=float(row["availability"]),
                        last_successful_inference=ts,
                        monitoring_status=monitoring_status(error_rate, drift),
                    )
                )
        db.commit()
        print("Seed complete")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
