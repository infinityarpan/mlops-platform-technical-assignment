from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domain.auth import APPROVE_ROLES, WRITE_ROLES, require_role
from app.domain.deployment import assert_can_deploy, assert_can_retry, assert_can_rollback
from app.domain.enums import DeploymentStatus, Environment, LifecycleStage, Role
from app.domain.errors import ConflictError, NotFoundError
from app.models.entities import Deployment, DeploymentEvent, new_id
from app.services.mlflow_registry import MLflowRegistry, get_model_registry
from app.services.registry_records import ModelRecord, VersionRecord

logger = structlog.get_logger()


def _now() -> datetime:
    return datetime.now(UTC)


def _registry(registry: MLflowRegistry | None = None) -> MLflowRegistry:
    return registry or get_model_registry()


def add_event(db: Session, deployment: Deployment, event: str, message: str | None = None) -> None:
    db.add(
        DeploymentEvent(
            deployment_id=deployment.id,
            event=event,
            status=deployment.status,
            message=message,
        )
    )


def create_model(db: Session, payload, registry: MLflowRegistry | None = None) -> ModelRecord:
    del db
    return _registry(registry).create_model(payload)


def list_models(db: Session, registry: MLflowRegistry | None = None) -> list[ModelRecord]:
    del db
    return _registry(registry).list_models()


def get_model_with_versions(db: Session, model_id: str, registry: MLflowRegistry | None = None) -> ModelRecord:
    del db
    return _registry(registry).get_model(model_id, include_versions=True)


def register_version(db: Session, model_id: str, payload, registry: MLflowRegistry | None = None) -> VersionRecord:
    del db
    return _registry(registry).register_version(model_id, payload)


def list_versions(db: Session, model_id: str, registry: MLflowRegistry | None = None) -> list[VersionRecord]:
    del db
    return _registry(registry).list_versions(model_id)


def promote_to_staging(
    db: Session,
    model_id: str,
    version: str,
    role: Role,
    registry: MLflowRegistry | None = None,
) -> VersionRecord:
    require_role(role, APPROVE_ROLES)
    del db
    return _registry(registry).promote_to_staging(model_id, version)


def transition_stage(
    db: Session,
    model_id: str,
    version: str,
    target: LifecycleStage,
    role: Role,
    registry: MLflowRegistry | None = None,
) -> VersionRecord:
    require_role(role, WRITE_ROLES | APPROVE_ROLES)
    del db
    return _registry(registry).transition_stage(model_id, version, target)


def create_deployment(
    db: Session,
    payload,
    role: Role,
    correlation_id: str,
    enqueue,
    registry: MLflowRegistry | None = None,
) -> tuple[Deployment, bool]:
    require_role(role, WRITE_ROLES)
    model_registry = _registry(registry)
    if payload.idempotency_key:
        existing = db.scalar(select(Deployment).where(Deployment.idempotency_key == payload.idempotency_key))
        if existing is not None:
            logger.info("idempotent_replay", deployment_id=existing.id, key=payload.idempotency_key)
            return existing, True
    version = model_registry.get_version(payload.model_id, payload.version)
    assert_can_deploy(
        stage=version.lifecycle_stage,
        environment=payload.environment,
    )
    deployment = Deployment(
        id=new_id(),
        model_id=payload.model_id,
        version_id=version.id,
        version=version.version,
        environment=payload.environment,
        status=DeploymentStatus.REQUESTED,
        idempotency_key=payload.idempotency_key,
        simulate_failure=payload.simulate_failure,
        correlation_id=correlation_id,
        created_at=_now(),
    )
    db.add(deployment)
    add_event(db, deployment, "deployment_requested", "Deployment accepted for asynchronous processing.")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "active-deployment-exists",
            "Conflicting in-flight deployment",
            "An active deployment already exists for this model and environment, or the idempotency key was reused.",
        ) from exc
    db.refresh(deployment)
    enqueue(deployment.id)
    logger.info("deployment_enqueued", deployment_id=deployment.id, model_id=payload.model_id)
    return get_deployment(db, deployment.id), False


def list_deployments(db: Session, model_id: str | None = None, environment: str | None = None) -> list[Deployment]:
    stmt = select(Deployment).options(selectinload(Deployment.events)).order_by(Deployment.created_at.desc())
    if model_id:
        stmt = stmt.where(Deployment.model_id == model_id)
    if environment:
        stmt = stmt.where(Deployment.environment == environment)
    return list(db.scalars(stmt).all())


def get_deployment(db: Session, deployment_id: str) -> Deployment:
    db.expire_all()
    row = db.scalar(
        select(Deployment).options(selectinload(Deployment.events)).where(Deployment.id == deployment_id)
    )
    if row is None:
        raise NotFoundError("Deployment not found", f"No deployment exists with id '{deployment_id}'.")
    return row


def retry_deployment(
    db: Session,
    deployment_id: str,
    role: Role,
    enqueue,
    registry: MLflowRegistry | None = None,
) -> Deployment:
    del registry
    require_role(role, WRITE_ROLES)
    row = get_deployment(db, deployment_id)
    assert_can_retry(status=DeploymentStatus(row.status))
    row.status = DeploymentStatus.REQUESTED
    row.failure_reason = None
    row.failure_class = None
    row.simulate_failure = False
    add_event(db, row, "deployment_retry_requested", "Retry accepted.")
    db.commit()
    enqueue(row.id)
    logger.info("deployment_retry", deployment_id=row.id)
    return get_deployment(db, deployment_id)


def rollback_deployment(
    db: Session,
    deployment_id: str,
    role: Role,
    enqueue,
    registry: MLflowRegistry | None = None,
) -> Deployment:
    del registry
    require_role(role, WRITE_ROLES)
    current = get_deployment(db, deployment_id)
    previous = db.scalar(
        select(Deployment)
        .where(
            Deployment.model_id == current.model_id,
            Deployment.environment == current.environment,
            Deployment.status == DeploymentStatus.SUCCEEDED,
            Deployment.id != current.id,
        )
        .order_by(Deployment.created_at.desc(), Deployment.id.desc())
    )
    assert_can_rollback(
        status=DeploymentStatus(current.status),
        environment=Environment(current.environment),
        has_previous=previous is not None,
    )
    assert previous is not None
    current.status = DeploymentStatus.ROLLED_BACK
    add_event(db, current, "rollback_initiated", f"Restoring version {previous.version}.")
    restore = Deployment(
        id=new_id(),
        model_id=previous.model_id,
        version_id=previous.version_id,
        version=previous.version,
        environment=previous.environment,
        status=DeploymentStatus.REQUESTED,
        previous_deployment_id=current.id,
        correlation_id=current.correlation_id,
    )
    db.add(restore)
    add_event(db, restore, "rollback_restore_requested", f"Rolling back to {previous.version}.")
    db.commit()
    enqueue(restore.id)
    logger.info("rollback_enqueued", from_id=current.id, restore_id=restore.id, version=previous.version)
    return get_deployment(db, restore.id)


def list_metrics(
    db: Session,
    model_id: str,
    version: str | None = None,
    environment: str | None = None,
    registry: MLflowRegistry | None = None,
) -> list[dict]:
    from app.services.prometheus_query import get_prometheus_client, monitoring_status

    del db
    _registry(registry).get_model(model_id)
    try:
        points = get_prometheus_client().list_metric_points(
            model_id,
            version=version,
            environment=environment,
        )
    except Exception as exc:
        logger.warning("prometheus_query_failed", model_id=model_id, error=str(exc))
        return []
    return [
        {
            "timestamp": point.timestamp,
            "model_id": point.model_id,
            "version": point.version,
            "environment": point.environment,
            "latency_ms": point.latency_ms,
            "throughput_rpm": point.throughput_rpm,
            "error_rate": point.error_rate,
            "quality_score": point.quality_score,
            "drift_score": point.drift_score,
            "availability": point.availability,
            "last_successful_inference": point.timestamp,
            "monitoring_status": monitoring_status(point.error_rate, point.drift_score),
        }
        for point in points
    ]


def process_deployment(
    db: Session,
    deployment_id: str,
    delay_seconds: float = 0.0,
    registry: MLflowRegistry | None = None,
) -> Deployment:
    import time

    from app.workers.runtime import SimulatedModelRuntime

    model_registry = _registry(registry)
    row = db.get(Deployment, deployment_id)
    if row is None:
        raise NotFoundError("Deployment not found", f"No deployment exists with id '{deployment_id}'.")
    try:
        version = model_registry.get_version(row.model_id, row.version)
    except NotFoundError as exc:
        row.status = DeploymentStatus.FAILED
        row.failure_reason = exc.detail
        row.failure_class = "version_not_found"
        add_event(db, row, "version_not_found", exc.detail)
        db.commit()
        return row

    row.status = DeploymentStatus.VALIDATING
    add_event(db, row, "validation_started", "Checking approval and environment controls.")
    db.commit()
    if delay_seconds:
        time.sleep(delay_seconds)

    if row.previous_deployment_id and version.lifecycle_stage == LifecycleStage.NONE:
        model_registry.transition_stage(row.model_id, row.version, LifecycleStage.STAGING)
        version = model_registry.get_version(row.model_id, row.version)

    try:
        assert_can_deploy(
            stage=version.lifecycle_stage,
            environment=Environment(row.environment),
        )
    except ConflictError as exc:
        row.status = DeploymentStatus.FAILED
        row.failure_reason = exc.detail
        row.failure_class = "approval_validation_failed"
        add_event(db, row, "approval_validation_failed", exc.detail)
        db.commit()
        return row

    row.status = DeploymentStatus.DEPLOYING
    add_event(db, row, "runtime_rollout_started", "Calling simulated model runtime.")
    db.commit()
    if delay_seconds:
        time.sleep(delay_seconds)

    result = SimulatedModelRuntime().deploy(
        model_id=row.model_id,
        version=row.version,
        environment=row.environment,
        simulate_failure=row.simulate_failure,
    )
    if not result.ok:
        row.status = DeploymentStatus.FAILED
        row.failure_reason = result.message
        row.failure_class = result.failure_class
        add_event(db, row, result.failure_class or "runtime_failed", result.message)
        db.commit()
        return row

    row.status = DeploymentStatus.SUCCEEDED
    row.failure_reason = None
    row.failure_class = None
    target_stage = (
        LifecycleStage.PRODUCTION if row.environment == Environment.PRODUCTION else LifecycleStage.STAGING
    )
    model_registry.set_lifecycle_stage_after_deploy(row.model_id, row.version, target_stage)
    add_event(db, row, "deployment_completed", result.message)
    db.commit()
    logger.info("deployment_succeeded", deployment_id=row.id, stage=str(target_stage))
    return row
