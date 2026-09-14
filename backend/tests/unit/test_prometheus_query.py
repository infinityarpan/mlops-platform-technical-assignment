from datetime import UTC, datetime

from app.services.prometheus_query import MetricPoint, monitoring_status


def test_monitoring_status_thresholds():
    assert monitoring_status(0.01, 0.1) == "healthy"
    assert monitoring_status(0.03, 0.1) == "degraded"
    assert monitoring_status(0.01, 0.4) == "degraded"


def test_metric_point_fields():
    point = MetricPoint(
        timestamp=datetime.now(UTC),
        model_id="pump-failure-predictor",
        version="1.0.0",
        environment="production",
        latency_ms=90.0,
        throughput_rpm=1000.0,
        error_rate=0.01,
        quality_score=0.9,
        drift_score=0.2,
        availability=99.5,
    )
    assert point.model_id == "pump-failure-predictor"
