from fastapi.testclient import TestClient


def test_worker_failure_classification(client: TestClient):
    headers = {"X-Actor-Role": "admin"}
    created = client.post("/models", json={"id": "runtime-demo", "name": "M", "owner": "O"}, headers=headers)
    assert created.status_code == 201
    client.post("/models/runtime-demo/versions", json={"version": "1.0.0", "artifact_uri": "s3://a"}, headers=headers)
    client.post("/models/runtime-demo/versions/1.0.0/promote-to-staging", headers=headers)
    resp = client.post(
        "/deployments",
        json={"model_id": "runtime-demo", "version": "1.0.0", "environment": "staging", "simulate_failure": True},
        headers=headers,
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["failure_class"] == "runtime_timeout"
    events = client.get(f"/deployments/{resp.json()['id']}/events")
    assert any(e["event"] == "runtime_timeout" for e in events.json())
