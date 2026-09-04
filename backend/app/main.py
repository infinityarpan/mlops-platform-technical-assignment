from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response

from app.api import deployments, health, models
from app.domain.errors import DomainError
from app.logging import CorrelationIdMiddleware, configure_logging

configure_logging()

REQUESTS = Counter("mlops_http_requests_total", "HTTP requests", ["method", "path", "status"])

app = FastAPI(
    title="MLOps Platform API",
    version="1.0.0",
    description="Registry, deployment, monitoring and rollback for industrial ML models.",
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(deployments.router)
app.include_router(health.router)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    REQUESTS.labels(request.method, request.url.path, str(exc.status)).inc()
    return JSONResponse(
        status_code=exc.status,
        content={
            "type": f"https://mlops.local/errors/{exc.code}",
            "title": exc.title,
            "status": exc.status,
            "detail": exc.detail,
            "instance": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://mlops.local/errors/validation",
            "title": "Request validation failed",
            "status": 422,
            "detail": exc.errors(),
            "instance": request.url.path,
        },
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
