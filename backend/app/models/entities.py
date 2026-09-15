from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import DeploymentStatus, Environment


def new_id() -> str:
    return str(uuid4())


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
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(160), nullable=False)
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
