from fastapi.testclient import TestClient


def test_health_exposes_database_and_fail_safe_state(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "DEGRADED"
    assert body["components"]["database"]["state"] == "HEALTHY"
    assert body["components"]["gate"]["state"] == "DEGRADED"


def test_root_has_no_operational_controls(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
