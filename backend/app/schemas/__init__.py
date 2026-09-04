from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import DeploymentStatus, Environment, LifecycleStage


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ModelCreate(BaseModel):
    id: str = Field(min_length=3, max_length=128, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class VersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=64)
    framework: Optional[str] = None
    algorithm: Optional[str] = None
    artifact_uri: str = Field(min_length=1, max_length=512)
    training_data_ref: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class VersionRead(ORMModel):
    id: str
    model_id: str
    version: str
    framework: Optional[str]
    algorithm: Optional[str]
    artifact_uri: str
    training_data_ref: Optional[str]
    tags: list[str]
    extra_metadata: dict[str, Any]
    approved: bool
    lifecycle_stage: LifecycleStage
    lock_version: int
    created_at: datetime
    updated_at: datetime


class ModelRead(ORMModel):
    id: str
    name: str
    owner: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    versions: list[VersionRead] = Field(default_factory=list)


class ModelSummary(ORMModel):
    id: str
    name: str
    owner: str
    description: Optional[str]
    created_at: datetime
    version_count: int = 0
    production_version: Optional[str] = None


class PromoteRequest(BaseModel):
    target_stage: LifecycleStage


class DeploymentCreate(BaseModel):
    model_id: str
    version: str
    environment: Environment
    simulate_failure: bool = False
    idempotency_key: Optional[str] = Field(default=None, max_length=128)


class DeploymentEventRead(ORMModel):
    id: str
    event: str
    status: DeploymentStatus
    message: Optional[str]
    created_at: datetime


class DeploymentRead(ORMModel):
    id: str
    model_id: str
    version_id: str
    version: str
    environment: Environment
    status: DeploymentStatus
    idempotency_key: Optional[str]
    previous_deployment_id: Optional[str]
    failure_reason: Optional[str]
    failure_class: Optional[str]
    simulate_failure: bool
    correlation_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    events: list[DeploymentEventRead] = Field(default_factory=list)


class MetricSampleRead(ORMModel):
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
    last_successful_inference: Optional[datetime]
    monitoring_status: str


class MetricsResponse(BaseModel):
    model_id: str
    samples: list[MetricSampleRead]
    latest: Optional[MetricSampleRead] = None


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: str
