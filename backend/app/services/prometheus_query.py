from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

OPS_METRICS = {
    "latency_ms": "mlops_inference_latency_ms",
    "throughput_rpm": "mlops_inference_throughput_rpm",
    "error_rate": "mlops_inference_error_rate",
    "quality_score": "mlops_inference_quality_score",
    "availability": "mlops_inference_availability_percent",
}
DRIFT_METRIC = "mlops_model_drift_score"


@dataclass(frozen=True)
class MetricPoint:
    timestamp: datetime
    model_id: str
    version: str
    environment: str
    latency_ms: float
    throughput_rpm: float
    error_rate: float
    quality_score: float
    drift_score: float
    availability: float


def monitoring_status(error_rate: float, drift_score: float) -> str:
    if error_rate > settings.metrics_degraded_error_rate or drift_score > settings.metrics_degraded_drift_score:
        return "degraded"
    return "healthy"


def _to_datetime(raw: float | int | str) -> datetime:
    return datetime.fromtimestamp(float(raw), tz=UTC)


def _label_filters(model_id: str, version: str | None, environment: str | None) -> str:
    filters = [f'model_id="{model_id}"']
    if version:
        filters.append(f'version="{version}"')
    if environment:
        filters.append(f'environment="{environment}"')
    return "{" + ",".join(filters) + "}"


class PrometheusQueryClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self._base_url = (base_url or settings.prometheus_url).rstrip("/")
        self._timeout = timeout

    def _query_range(self, query: str, *, start: datetime, end: datetime, step: str) -> list[dict]:
        response = httpx.get(
            f"{self._base_url}/api/v1/query_range",
            params={
                "query": query,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": step,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(payload.get("error", "Prometheus query failed"))
        return payload.get("data", {}).get("result", [])

    def _metric_series(
        self,
        metric_name: str,
        labels: str,
        *,
        start: datetime,
        end: datetime,
        step: str,
    ) -> dict[tuple[str, str, datetime], float]:
        series = self._query_range(f"{metric_name}{labels}", start=start, end=end, step=step)
        values: dict[tuple[str, str, datetime], float] = {}
        for item in series:
            metric = item.get("metric", {})
            version = metric.get("version", "unknown")
            environment = metric.get("environment", "production")
            for raw_ts, raw_value in item.get("values", []):
                key = (version, environment, _to_datetime(raw_ts))
                values[key] = float(raw_value)
        return values

    def list_metric_points(
        self,
        model_id: str,
        *,
        version: str | None = None,
        environment: str | None = None,
        lookback_days: int | None = None,
    ) -> list[MetricPoint]:
        labels = _label_filters(model_id, version, environment)
        lookback = lookback_days or settings.prometheus_metrics_lookback_days
        end = datetime.now(UTC)
        start = end - timedelta(days=lookback)
        step = settings.prometheus_query_step

        latency = self._metric_series(OPS_METRICS["latency_ms"], labels, start=start, end=end, step=step)
        if not latency:
            return []

        throughput = self._metric_series(OPS_METRICS["throughput_rpm"], labels, start=start, end=end, step=step)
        error_rate = self._metric_series(OPS_METRICS["error_rate"], labels, start=start, end=end, step=step)
        quality = self._metric_series(OPS_METRICS["quality_score"], labels, start=start, end=end, step=step)
        availability = self._metric_series(OPS_METRICS["availability"], labels, start=start, end=end, step=step)
        drift = self._metric_series(DRIFT_METRIC, labels, start=start, end=end, step=step)

        points: list[MetricPoint] = []
        for (ver, env, ts), latency_ms in sorted(latency.items(), key=lambda item: item[0][2]):
            if version and ver != version:
                continue
            if environment and env != environment:
                continue
            key = (ver, env, ts)
            points.append(
                MetricPoint(
                    timestamp=ts,
                    model_id=model_id,
                    version=ver,
                    environment=env,
                    latency_ms=latency_ms,
                    throughput_rpm=throughput.get(key, 0.0),
                    error_rate=error_rate.get(key, 0.0),
                    quality_score=quality.get(key, 0.0),
                    drift_score=drift.get(key, 0.0),
                    availability=availability.get(key, 0.0),
                )
            )
        return points


_client: PrometheusQueryClient | None = None


def get_prometheus_client() -> PrometheusQueryClient:
    global _client
    if _client is None:
        _client = PrometheusQueryClient()
    return _client


def set_prometheus_client(client: PrometheusQueryClient | None) -> None:
    global _client
    _client = client
