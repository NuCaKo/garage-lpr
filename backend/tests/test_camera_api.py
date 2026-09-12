from garage_lpr.camera.domain import CameraConnectionResult

CAMERA_PAYLOAD = {
    "name": "Garaj Giriş",
    "camera_type": "RTSP",
    "stream_url": "rtsp://192.0.2.1/live",
    "username": "operator",
    "password": "local-secret",
    "capture_fps_limit": 20,
    "detection_fps": 5,
    "requested_width": 1280,
    "requested_height": 720,
    "roi": {"x": 0.2, "y": 0.3, "width": 0.6, "height": 0.4},
    "active": False,
    "connection_timeout_seconds": 3,
    "reconnect_schedule_seconds": [1, 2, 5, 10, 30],
}


class SuccessfulConnectionTester:
    def test(self, configuration: object) -> CameraConnectionResult:
        return CameraConnectionResult(True, 18.5, 1280, 720, 24.9, "Frame received")


def test_camera_crud_does_not_expose_password(client) -> None:
    created = client.post("/api/v1/cameras", json=CAMERA_PAYLOAD)

    assert created.status_code == 201
    body = created.json()
    assert body["has_password"] is True
    assert "password" not in body
    assert "credentials_ciphertext" not in body
    camera_id = body["id"]

    listed = client.get("/api/v1/cameras")
    assert listed.status_code == 200
    assert listed.json()[0]["roi"]["x"] == 0.2

    updated_payload = {**CAMERA_PAYLOAD, "password": None, "name": "Garaj Giriş 1"}
    updated = client.put(f"/api/v1/cameras/{camera_id}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["has_password"] is True


def test_camera_connection_result_contains_operational_metrics(client) -> None:
    created = client.post("/api/v1/cameras", json=CAMERA_PAYLOAD)
    camera_id = created.json()["id"]
    client.app.state.camera_connection_tester = SuccessfulConnectionTester()

    response = client.post(f"/api/v1/cameras/{camera_id}/test-connection")

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "latency_ms": 18.5,
        "resolution": "1280×720",
        "fps": 24.9,
        "detail": "Frame received",
    }
