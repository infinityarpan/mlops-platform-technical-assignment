from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.domain.enums import DeploymentStatus, Environment, LifecycleStage

JSONType = JSON().with_variant(JSONB, "postgresql")


def new_id() -> str:
    return str(uuid4())


class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["ModelVersion"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_model_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    framework: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    algorithm: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    artifact_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    training_data_ref: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    extra_metadata: Mapped[dict] = mapped_column(JSONType, default=dict)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lifecycle_stage: Mapped[str] = mapped_column(String(32), default=LifecycleStage.DRAFT, nullable=False)
    lock_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    model: Mapped[Model] = relationship(back_populates="versions")


class Deployment(Base):
    __tablename__ = "deployments"
    __table_args__ = (
        Index(
            "uq_active_deployment_per_env",
            "model_id",
            "environment",
            unique=True,
            sqlite_where=text("status IN ('REQUESTED','VALIDATING','DEPLOYING')"),
            postgresql_where=text("status IN ('REQUESTED','VALIDATING','DEPLOYING')"),
        ),
        UniqueConstraint("idempotency_key", name="uq_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), default=Environment.STAGING, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=DeploymentStatus.REQUESTED, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    previous_deployment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_class: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    simulate_failure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["DeploymentEvent"]] = relationship(
        back_populates="deployment", cascade="all, delete-orphan", order_by="DeploymentEvent.created_at"
    )


class DeploymentEvent(Base):
    __tablename__ = "deployment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployments.id"), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deployment: Mapped[Deployment] = relationship(back_populates="events")


class MetricSample(Base):
    __tablename__ = "metric_samples"
    __table_args__ = (Index("ix_metrics_model_ts", "model_id", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    throughput_rpm: Mapped[float] = mapped_column(Float, nullable=False)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    drift_score: Mapped[float] = mapped_column(Float, nullable=False)
    availability: Mapped[float] = mapped_column(Float, nullable=False)
    last_successful_inference: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    monitoring_status: Mapped[str] = mapped_column(String(32), default="healthy", nullable=False)
