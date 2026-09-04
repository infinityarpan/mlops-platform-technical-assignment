from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import actor_role, db_session
from app.domain.enums import Role
from app.schemas import DeploymentCreate, DeploymentEventRead, DeploymentRead
from app.services import registry
from app.workers.celery_app import enqueue_deployment

router = APIRouter(prefix="/deployments", tags=["deployments"])


def get_enqueuer():
    return enqueue_deployment


@router.post("", response_model=DeploymentRead, status_code=202)
def create_deployment(
    payload: DeploymentCreate,
    request: Request,
    db: Session = Depends(db_session),
    role: Role = Depends(actor_role),
    enqueue=Depends(get_enqueuer),
):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    key = payload.idempotency_key or request.headers.get("Idempotency-Key")
    data = payload.model_copy(update={"idempotency_key": key})
    deployment, _replay = registry.create_deployment(db, data, role, correlation_id, enqueue)
    return registry.get_deployment(db, deployment.id)


@router.get("", response_model=list[DeploymentRead])
def list_deployments(
    model_id: str | None = None,
    environment: str | None = None,
    db: Session = Depends(db_session),
):
    return registry.list_deployments(db, model_id, environment)


@router.get("/{deployment_id}", response_model=DeploymentRead)
def get_deployment(deployment_id: str, db: Session = Depends(db_session)):
    return registry.get_deployment(db, deployment_id)


@router.get("/{deployment_id}/events", response_model=list[DeploymentEventRead])
def get_events(deployment_id: str, db: Session = Depends(db_session)):
    return registry.get_deployment(db, deployment_id).events


@router.post("/{deployment_id}/retry", response_model=DeploymentRead, status_code=202)
def retry_deployment(
    deployment_id: str,
    db: Session = Depends(db_session),
    role: Role = Depends(actor_role),
    enqueue=Depends(get_enqueuer),
):
    return registry.retry_deployment(db, deployment_id, role, enqueue)


@router.post("/{deployment_id}/rollback", response_model=DeploymentRead, status_code=202)
def rollback_deployment(
    deployment_id: str,
    db: Session = Depends(db_session),
    role: Role = Depends(actor_role),
    enqueue=Depends(get_enqueuer),
):
    return registry.rollback_deployment(db, deployment_id, role, enqueue)
