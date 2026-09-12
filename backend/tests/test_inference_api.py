from fastapi.testclient import TestClient


def test_inference_metrics_are_bounded_and_fail_closed_without_models(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/metrics/inference")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "CONFIGURATION_REQUIRED"
    assert body["frames_sampled"] == 0
    assert body["ocr_calls"] == 0
    assert body["frame_buffer_capacity"] == 1
    assert body["queue_size"] == 0
    assert body["detector_provider"] is None
