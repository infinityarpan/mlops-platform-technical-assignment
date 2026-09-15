import shutil
import uuid
from pathlib import Path

import pytest
from mlflow.tracking import MlflowClient

from app.domain.enums import LifecycleStage
from app.domain.errors import ConflictError, NotFoundError
from app.schemas import ModelCreate, VersionCreate
from app.services.mlflow_registry import MLflowRegistry
from app.services.mlflow_uri import mlflow_sqlite_uri

MLFLOW_UNIT_DIR = Path(__file__).resolve().parent / ".mlflow_unit"


@pytest.fixture
def registry():
    test_dir = MLFLOW_UNIT_DIR / uuid.uuid4().hex
    test_dir.mkdir(parents=True)
    yield MLflowRegistry(MlflowClient(tracking_uri=mlflow_sqlite_uri(test_dir)))
    shutil.rmtree(test_dir, ignore_errors=True)


def test_create_register_promote_to_staging_and_transition(registry: MLflowRegistry):
    registry.create_model(
        ModelCreate(id="pump-failure-predictor", name="Pump Failure Predictor", owner="Reliability")
    )
    version = registry.register_version(
        "pump-failure-predictor",
        VersionCreate(version="1.0.0", artifact_uri="s3://models/pump/1.0.0", framework="scikit-learn"),
    )
    assert version.lifecycle_stage == LifecycleStage.NONE

    promoted_to_staging = registry.promote_to_staging("pump-failure-predictor", "1.0.0")
    assert promoted_to_staging.lifecycle_stage == LifecycleStage.STAGING

    transitioned = registry.transition_stage("pump-failure-predictor", "1.0.0", LifecycleStage.PRODUCTION)
    assert transitioned.lifecycle_stage == LifecycleStage.PRODUCTION


def test_duplicate_model_and_version(registry: MLflowRegistry):
    payload = ModelCreate(id="valve-health-model", name="Valve", owner="Ops")
    registry.create_model(payload)
    with pytest.raises(ConflictError):
        registry.create_model(payload)

    version_payload = VersionCreate(version="3.0.0", artifact_uri="s3://models/v/3.0.0")
    registry.register_version("valve-health-model", version_payload)
    with pytest.raises(ConflictError):
        registry.register_version("valve-health-model", version_payload)


def test_missing_model(registry: MLflowRegistry):
    with pytest.raises(NotFoundError):
        registry.get_model("missing-model")
