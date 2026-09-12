from fastapi.testclient import TestClient


def test_runtime_settings_start_fail_safe(client: TestClient) -> None:
    response = client.get("/api/v1/system-settings")

    assert response.status_code == 200
    assert response.json()["simulation_mode"] is True
    assert response.json()["maintenance_mode"] is True
    assert response.json()["detection_fps"] == 5.0


def test_runtime_settings_are_validated_and_persisted(client: TestClient) -> None:
    current = client.get("/api/v1/system-settings").json()
    current["detection_fps"] = 4.0
    current["snapshot_enabled"] = True

    updated = client.put("/api/v1/system-settings", json=current)

    assert updated.status_code == 200
    assert client.get("/api/v1/system-settings").json()["detection_fps"] == 4.0
    assert (
        "disabled"
        not in client.get("/api/v1/health").json()["components"]["storage"]["detail"].lower()
    )


def test_unsafe_detection_rate_is_rejected(client: TestClient) -> None:
    current = client.get("/api/v1/system-settings").json()
    current["detection_fps"] = 100

    response = client.put("/api/v1/system-settings", json=current)

    assert response.status_code == 422
