from fastapi.testclient import TestClient

HEADERS = {"X-Actor-Role": "admin"}


def test_health(client: TestClient):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").status_code == 200


def test_register_approve_deploy_metrics_rollback(client: TestClient):
    model = client.post(
        "/models",
        json={"id": "pump-failure-predictor", "name": "Pump Failure Predictor", "owner": "Reliability"},
        headers=HEADERS,
    )
    assert model.status_code == 201
    v1 = client.post(
        "/models/pump-failure-predictor/versions",
        json={"version": "1.0.0", "artifact_uri": "s3://models/pump/1.0.0", "framework": "scikit-learn"},
        headers=HEADERS,
    )
    v2 = client.post(
        "/models/pump-failure-predictor/versions",
        json={"version": "2.0.0", "artifact_uri": "s3://models/pump/2.0.0", "framework": "scikit-learn"},
        headers=HEADERS,
    )
    assert v1.status_code == 201 and v2.status_code == 201

    approved = client.post(
        "/models/pump-failure-predictor/versions/2.0.0/approve",
        headers=HEADERS,
    )
    assert approved.status_code == 200
    assert approved.json()["approved"] is True

    client.post(
        "/models/pump-failure-predictor/versions/1.0.0/approve",
        headers=HEADERS,
    )

    client.post(
        "/models",
        json={"id": "compressor-anomaly-detector", "name": "Compressor", "owner": "CM"},
        headers=HEADERS,
    )
    client.post(
        "/models/compressor-anomaly-detector/versions",
        json={"version": "1.1.0", "artifact_uri": "s3://models/c/1.1.0"},
        headers=HEADERS,
    )
    forbidden = client.post(
        "/deployments",
        json={
            "model_id": "compressor-anomaly-detector",
            "version": "1.1.0",
            "environment": "production",
        },
        headers=HEADERS,
    )
    assert forbidden.status_code == 409
    assert "Unapproved" in forbidden.json()["title"] or "unapproved" in forbidden.json()["detail"].lower() or "Approve" in forbidden.json()["detail"]

    first = client.post(
        "/deployments",
        json={
            "model_id": "pump-failure-predictor",
            "version": "1.0.0",
            "environment": "production",
        },
        headers=HEADERS,
    )
    assert first.status_code == 202
    assert first.json()["status"] == "SUCCEEDED"

    second = client.post(
        "/deployments",
        json={
            "model_id": "pump-failure-predictor",
            "version": "2.0.0",
            "environment": "production",
        },
        headers=HEADERS,
    )
    assert second.status_code == 202
    assert second.json()["status"] == "SUCCEEDED"

    metrics = client.get("/models/pump-failure-predictor/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["samples"] == []

    rolled = client.post(f"/deployments/{second.json()['id']}/rollback", headers=HEADERS)
    assert rolled.status_code == 202
    assert rolled.json()["version"] == "1.0.0"
    assert rolled.json()["status"] == "SUCCEEDED"


def test_retry_failed_and_idempotency(client: TestClient):
    client.post("/models", json={"id": "valve-health-model", "name": "Valve", "owner": "Rel"}, headers=HEADERS)
    client.post(
        "/models/valve-health-model/versions",
        json={"version": "3.0.0", "artifact_uri": "s3://models/v/3.0.0"},
        headers=HEADERS,
    )
    client.post("/models/valve-health-model/versions/3.0.0/approve", headers=HEADERS)

    failed = client.post(
        "/deployments",
        json={
            "model_id": "valve-health-model",
            "version": "3.0.0",
            "environment": "staging",
            "simulate_failure": True,
            "idempotency_key": "valve-3-staging",
        },
        headers=HEADERS,
    )
    assert failed.status_code == 202
    assert failed.json()["status"] == "FAILED"

    replay = client.post(
        "/deployments",
        json={
            "model_id": "valve-health-model",
            "version": "3.0.0",
            "environment": "staging",
            "simulate_failure": True,
            "idempotency_key": "valve-3-staging",
        },
        headers=HEADERS,
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == failed.json()["id"]

    retried = client.post(f"/deployments/{failed.json()['id']}/retry", headers=HEADERS)
    assert retried.status_code == 202
    assert retried.json()["status"] == "SUCCEEDED"

    viewer = client.post(
        "/deployments",
        json={"model_id": "valve-health-model", "version": "3.0.0", "environment": "staging"},
        headers={"X-Actor-Role": "viewer"},
    )
    assert viewer.status_code == 403


def test_validation_error(client: TestClient):
    resp = client.post("/models", json={"id": "BAD ID", "name": "x", "owner": "y"}, headers=HEADERS)
    assert resp.status_code == 422
