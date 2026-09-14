from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from app.config import settings
from app.services.inference_metrics import record_drift_score

logger = structlog.get_logger()


def _dataset_path(model_id: str, kind: str) -> Path:
    return settings.drift_data_dir / f"{model_id}_{kind}.csv"


def _ensure_feature_datasets(model_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    settings.drift_data_dir.mkdir(parents=True, exist_ok=True)
    reference_path = _dataset_path(model_id, "reference")
    current_path = _dataset_path(model_id, "current")
    if not reference_path.exists() or not current_path.exists():
        _generate_default_datasets(model_id, reference_path, current_path)
    reference = pd.read_csv(reference_path)
    current = pd.read_csv(current_path)
    return reference, current


def _generate_default_datasets(model_id: str, reference_path: Path, current_path: Path) -> None:
    rng = np.random.default_rng(abs(hash(model_id)) % (2**32))
    columns = ["sensor_a", "sensor_b", "sensor_c", "operating_load"]
    reference = pd.DataFrame({column: rng.normal(loc=0.0, scale=1.0, size=500) for column in columns})
    shift = 0.35 if "compressor" in model_id else 0.15
    current = pd.DataFrame(
        {column: rng.normal(loc=shift, scale=1.05, size=300) for column in columns}
    )
    reference.to_csv(reference_path, index=False)
    current.to_csv(current_path, index=False)
    logger.info("drift_datasets_generated", model_id=model_id)


def _extract_drift_score(report) -> float:
    payload = report.as_dict()
    for metric in payload.get("metrics", []):
        if metric.get("metric") == "DatasetDriftMetric":
            result = metric.get("result", {})
            if "share_of_drifted_columns" in result:
                return float(result["share_of_drifted_columns"])
            if "drift_share" in result:
                return float(result["drift_share"])
    return 0.0


def compute_drift_score(model_id: str) -> float:
    reference, current = _ensure_feature_datasets(model_id)
    from evidently.legacy.metric_preset import DataDriftPreset
    from evidently.legacy.report import Report

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)
    score = _extract_drift_score(report)
    logger.info("evidently_drift_computed", model_id=model_id, drift_score=score)
    return max(0.0, min(score, 1.0))


def publish_drift_scores(
    *,
    model_id: str,
    version: str,
    environment: str = "production",
) -> float:
    score = compute_drift_score(model_id)
    record_drift_score(model_id=model_id, version=version, environment=environment, drift_score=score)
    return score
