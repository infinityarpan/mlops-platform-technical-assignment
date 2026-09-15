import os

os.environ.setdefault("AUTH_MODE", "header")

import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mlflow.tracking import MlflowClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deployments import get_enqueuer
from app.db import get_db
from app.main import app
from app.models.entities import Base
from app.services.mlflow_registry import MLflowRegistry, set_model_registry
from app.services.mlflow_uri import mlflow_sqlite_uri
from app.services.prometheus_query import PrometheusQueryClient, set_prometheus_client
from app.services.registry import process_deployment

MLFLOW_TEST_DIR = Path(__file__).resolve().parent / ".mlflow_test"


class FakePrometheusClient(PrometheusQueryClient):
    def list_metric_points(self, model_id: str, *, version=None, environment=None, lookback_days=None):
        del model_id, version, environment, lookback_days
        return []


@pytest.fixture(autouse=True)
def fake_prometheus():
    client = FakePrometheusClient(base_url="http://prometheus.test")
    set_prometheus_client(client)
    yield
    set_prometheus_client(None)


@pytest.fixture
def client():
    test_dir = MLFLOW_TEST_DIR / uuid.uuid4().hex
    test_dir.mkdir(parents=True)
    set_model_registry(
        MLflowRegistry(MlflowClient(tracking_uri=mlflow_sqlite_uri(test_dir)))
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    def enqueue(deployment_id: str) -> None:
        db = testing_session()
        try:
            process_deployment(db, deployment_id, delay_seconds=0)
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_enqueuer] = lambda: enqueue
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    set_model_registry(None)
    shutil.rmtree(test_dir, ignore_errors=True)
