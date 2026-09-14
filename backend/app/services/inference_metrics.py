from __future__ import annotations

from prometheus_client import CollectorRegistry, Gauge

INFERENCE_REGISTRY = CollectorRegistry()

LATENCY_MS = Gauge(
    "mlops_inference_latency_ms",
    "Inference latency in milliseconds",
    ["model_id", "version", "environment"],
    registry=INFERENCE_REGISTRY,
)
THROUGHPUT_RPM = Gauge(
    "mlops_inference_throughput_rpm",
    "Inference throughput in requests per minute",
    ["model_id", "version", "environment"],
    registry=INFERENCE_REGISTRY,
)
ERROR_RATE = Gauge(
    "mlops_inference_error_rate",
    "Inference error rate (0-1)",
    ["model_id", "version", "environment"],
    registry=INFERENCE_REGISTRY,
)
QUALITY_SCORE = Gauge(
    "mlops_inference_quality_score",
    "Model quality score (0-1)",
    ["model_id", "version", "environment"],
    registry=INFERENCE_REGISTRY,
)
AVAILABILITY = Gauge(
    "mlops_inference_availability_percent",
    "Service availability percentage",
    ["model_id", "version", "environment"],
    registry=INFERENCE_REGISTRY,
)
DRIFT_SCORE = Gauge(
    "mlops_model_drift_score",
    "Evidently data drift score (0-1, higher is more drift)",
    ["model_id", "version", "environment"],
    registry=INFERENCE_REGISTRY,
)


def record_operational_sample(
    *,
    model_id: str,
    version: str,
    environment: str,
    latency_ms: float,
    throughput_rpm: float,
    error_rate: float,
    quality_score: float,
    availability: float,
) -> None:
    labels = (model_id, version, environment)
    LATENCY_MS.labels(*labels).set(latency_ms)
    THROUGHPUT_RPM.labels(*labels).set(throughput_rpm)
    ERROR_RATE.labels(*labels).set(error_rate)
    QUALITY_SCORE.labels(*labels).set(quality_score)
    AVAILABILITY.labels(*labels).set(availability)


def record_drift_score(*, model_id: str, version: str, environment: str, drift_score: float) -> None:
    DRIFT_SCORE.labels(model_id, version, environment).set(drift_score)
