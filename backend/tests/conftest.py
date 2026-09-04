import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deployments import get_enqueuer
from app.db import get_db
from app.main import app
from app.models.entities import Base
from app.services.registry import process_deployment


@pytest.fixture
def client():
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
