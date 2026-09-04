from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domain.auth import APPROVE_ROLES, WRITE_ROLES, require_role
from app.domain.deployment import assert_can_deploy, assert_can_retry, assert_can_rollback
from app.domain.enums import DeploymentStatus, Environment, LifecycleStage, Role
from app.domain.errors import ConflictError, NotFoundError
from app.domain.lifecycle import assert_can_approve, assert_can_promote
from app.models.entities import Deployment, DeploymentEvent, MetricSample, Model, ModelVersion, new_id

logger = structlog.get_logger()


def _now() -> datetime:
    return datetime.now(UTC)


def add_event(db: Session, deployment: Deployment, event: str, message: str | None = None) -> None:
    db.add(
        DeploymentEvent(
            deployment_id=deployment.id,
            event=event,
            status=deployment.status,
            message=message,
        )
    )


def get_model(db: Session, model_id: str) -> Model:
    model = db.get(Model, model_id)
    if model is None:
        raise NotFoundError("Model not found", f"No model exists with id '{model_id}'.")
    return model


def get_version(db: Session, model_id: str, version: str) -> ModelVersion:
    row = db.scalar(
        select(ModelVersion).where(ModelVersion.model_id == model_id, ModelVersion.version == version)
    )
    if row is None:
        raise NotFoundError("Version not found", f"Model '{model_id}' has no version '{version}'.")
    return row


def create_model(db: Session, payload) -> Model:
    if db.get(Model, payload.id) is not None:
        raise ConflictError("model-exists", "Model already exists", f"Model '{payload.id}' is already registered.")
    model = Model(id=payload.id, name=payload.name, owner=payload.owner, description=payload.description)
    db.add(model)
    db.commit()
    db.refresh(model)
    logger.info("model_created", model_id=model.id)
    return model


def list_models(db: Session) -> list[Model]:
    return list(db.scalars(select(Model).order_by(Model.name)).all())


def get_model_with_versions(db: Session, model_id: str) -> Model:
    model = db.scalar(select(Model).options(selectinload(Model.versions)).where(Model.id == model_id))
    if model is None:
        raise NotFoundError("Model not found", f"No model exists with id '{model_id}'.")
    return model


def register_version(db: Session, model_id: str, payload) -> ModelVersion:
    get_model(db, model_id)
    existing = db.scalar(
        select(ModelVersion).where(ModelVersion.model_id == model_id, ModelVersion.version == payload.version)
    )
    if existing is not None:
        raise ConflictError(
            "version-exists",
            "Version already exists",
            f"Version '{payload.version}' is already registered for '{model_id}'.",
        )
    row = ModelVersion(
        model_id=model_id,
        version=payload.version,
        framework=payload.framework,
        algorithm=payload.algorithm,
        artifact_uri=payload.artifact_uri,
        training_data_ref=payload.training_data_ref,
        tags=payload.tags,
        extra_metadata=payload.extra_metadata,
        approved=False,
        lifecycle_stage=LifecycleStage.DRAFT,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("version_registered", model_id=model_id, version=row.version)
    return row


def list_versions(db: Session, model_id: str) -> list[ModelVersion]:
    get_model(db, model_id)
    return list(
        db.scalars(
            select(ModelVersion).where(ModelVersion.model_id == model_id).order_by(ModelVersion.created_at)
        ).all()
    )


def approve_version(db: Session, model_id: str, version: str, role: Role) -> ModelVersion:
    require_role(role, APPROVE_ROLES)
    row = get_version(db, model_id, version)
    assert_can_approve(approved=row.approved, stage=LifecycleStage(row.lifecycle_stage))
    row.approved = True
    if LifecycleStage(row.lifecycle_stage) in {LifecycleStage.DRAFT, LifecycleStage.VALIDATED}:
        row.lifecycle_stage = LifecycleStage.APPROVED
    row.lock_version += 1
    db.commit()
    db.refresh(row)
    logger.info("version_approved", model_id=model_id, version=version, actor_role=str(role))
    return row


def promote_version(db: Session, model_id: str, version: str, target: LifecycleStage, role: Role) -> ModelVersion:
    require_role(role, WRITE_ROLES | APPROVE_ROLES)
    row = get_version(db, model_id, version)
    current = LifecycleStage(row.lifecycle_stage)
    assert_can_promote(current=current, target=target)
    if target in {LifecycleStage.STAGING, LifecycleStage.PRODUCTION} and not row.approved:
        raise ConflictError(
            "unapproved-promotion",
            "Version is not approved",
            "Approve the version before promoting to staging or production.",
        )
    row.lifecycle_stage = target
    if target == LifecycleStage.APPROVED:
        row.approved = True
    row.lock_version += 1
    db.commit()
    db.refresh(row)
    logger.info("version_promoted", model_id=model_id, version=version, stage=str(target))
    return row


def create_deployment(
    db: Session,
    payload,
    role: Role,
    correlation_id: str,
    enqueue,
) -> tuple[Deployment, bool]:
    require_role(role, WRITE_ROLES)
    if payload.idempotency_key:
        existing = db.scalar(select(Deployment).where(Deployment.idempotency_key == payload.idempotency_key))
        if existing is not None:
            logger.info("idempotent_replay", deployment_id=existing.id, key=payload.idempotency_key)
            return existing, True
    version = get_version(db, payload.model_id, payload.version)
    assert_can_deploy(
        approved=version.approved,
        stage=LifecycleStage(version.lifecycle_stage),
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


def retry_deployment(db: Session, deployment_id: str, role: Role, enqueue) -> Deployment:
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


def rollback_deployment(db: Session, deployment_id: str, role: Role, enqueue) -> Deployment:
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


def list_metrics(db: Session, model_id: str, version: str | None = None, environment: str | None = None):
    get_model(db, model_id)
    stmt = select(MetricSample).where(MetricSample.model_id == model_id).order_by(MetricSample.timestamp)
    if version:
        stmt = stmt.where(MetricSample.version == version)
    if environment:
        stmt = stmt.where(MetricSample.environment == environment)
    return list(db.scalars(stmt).all())


def process_deployment(db: Session, deployment_id: str, delay_seconds: float = 0.0) -> Deployment:
    import time

    from app.workers.runtime import SimulatedModelRuntime

    row = db.get(Deployment, deployment_id)
    if row is None:
        raise NotFoundError("Deployment not found", f"No deployment exists with id '{deployment_id}'.")
    version = db.get(ModelVersion, row.version_id)
    if version is None:
        raise NotFoundError("Version not found", "Deployment references a missing version.")

    row.status = DeploymentStatus.VALIDATING
    add_event(db, row, "validation_started", "Checking approval and environment controls.")
    db.commit()
    if delay_seconds:
        time.sleep(delay_seconds)

    try:
        assert_can_deploy(
            approved=version.approved,
            stage=LifecycleStage(version.lifecycle_stage),
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
        LifecycleStage.PRODUCTION
        if row.environment == Environment.PRODUCTION
        else LifecycleStage.STAGING
    )
    version.lifecycle_stage = target_stage
    version.lock_version += 1
    add_event(db, row, "deployment_completed", result.message)
    db.commit()
    logger.info("deployment_succeeded", deployment_id=row.id, stage=str(target_stage))
    return row
