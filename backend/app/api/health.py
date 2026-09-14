from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas import HealthResponse, ReadyResponse
from app.services.mlflow_registry import get_model_registry

router = APIRouter(tags=["ops"])


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
def ready(db: Session = Depends(db_session)):
    db.execute(text("SELECT 1"))
    get_model_registry().list_models()
    return ReadyResponse(status="ready", database="ok")
