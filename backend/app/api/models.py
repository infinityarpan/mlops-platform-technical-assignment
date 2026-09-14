from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import actor_role, db_session
from app.domain.enums import LifecycleStage, Role
from app.schemas import (
    ModelCreate,
    ModelRead,
    ModelSummary,
    StageTransitionRequest,
    VersionCreate,
    VersionRead,
)
from app.services import registry

router = APIRouter(prefix="/models", tags=["models"])


@router.post("", response_model=ModelRead, status_code=201)
def create_model(payload: ModelCreate, db: Session = Depends(db_session), role: Role = Depends(actor_role)):
    from app.domain.auth import WRITE_ROLES, require_role

    require_role(role, WRITE_ROLES)
    model = registry.create_model(db, payload)
    return registry.get_model_with_versions(db, model.id)


@router.get("", response_model=list[ModelSummary])
def list_models(db: Session = Depends(db_session)):
    models = registry.list_models(db)
    summaries = []
    for model in models:
        versions = registry.list_versions(db, model.id)
        production = next((v.version for v in versions if v.lifecycle_stage == LifecycleStage.PRODUCTION), None)
        summaries.append(
            ModelSummary(
                id=model.id,
                name=model.name,
                owner=model.owner,
                description=model.description,
                created_at=model.created_at,
                version_count=len(versions),
                production_version=production,
            )
        )
    return summaries


@router.get("/{model_id}", response_model=ModelRead)
def get_model(model_id: str, db: Session = Depends(db_session)):
    return registry.get_model_with_versions(db, model_id)


@router.post("/{model_id}/versions", response_model=VersionRead, status_code=201)
def register_version(
    model_id: str,
    payload: VersionCreate,
    db: Session = Depends(db_session),
    role: Role = Depends(actor_role),
):
    from app.domain.auth import WRITE_ROLES, require_role

    require_role(role, WRITE_ROLES)
    return registry.register_version(db, model_id, payload)


@router.get("/{model_id}/versions", response_model=list[VersionRead])
def list_versions(model_id: str, db: Session = Depends(db_session)):
    return registry.list_versions(db, model_id)


@router.post("/{model_id}/versions/{version}/promote-to-staging", response_model=VersionRead)
def promote_to_staging(
    model_id: str,
    version: str,
    db: Session = Depends(db_session),
    role: Role = Depends(actor_role),
):
    return registry.promote_to_staging(db, model_id, version, role)


@router.post("/{model_id}/versions/{version}/transition-stage", response_model=VersionRead)
def transition_stage(
    model_id: str,
    version: str,
    payload: StageTransitionRequest,
    db: Session = Depends(db_session),
    role: Role = Depends(actor_role),
):
    return registry.transition_stage(db, model_id, version, payload.target_stage, role)


@router.get("/{model_id}/metrics")
def get_metrics(
    model_id: str,
    version: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    db: Session = Depends(db_session),
):
    from app.schemas import MetricSampleRead, MetricsResponse

    samples = registry.list_metrics(db, model_id, version, environment)
    parsed = [MetricSampleRead.model_validate(sample) for sample in samples]
    return MetricsResponse(model_id=model_id, samples=parsed, latest=parsed[-1] if parsed else None)
