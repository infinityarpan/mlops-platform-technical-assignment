from __future__ import annotations

from prometheus_client import push_to_gateway

from app.config import settings
from app.services.inference_metrics import INFERENCE_REGISTRY

PUSH_JOB = "mlops_inference"


def push_inference_metrics() -> None:
    push_to_gateway(
        settings.pushgateway_url,
        job=PUSH_JOB,
        registry=INFERENCE_REGISTRY,
    )
