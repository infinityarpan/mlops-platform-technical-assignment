from prometheus_client import CollectorRegistry, Counter

CONTROL_PLANE_REGISTRY = CollectorRegistry()

REQUESTS = Counter(
    "mlops_http_requests_total",
    "HTTP requests handled by the control plane API",
    ["method", "path", "status"],
    registry=CONTROL_PLANE_REGISTRY,
)
