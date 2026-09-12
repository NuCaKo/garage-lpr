from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from garage_lpr.gate.orchestration import (
    DatabaseGateTargetResolver,
    GateOrchestrationOutcome,
)


def test_mock_gate_crud_and_connection_test(client: TestClient) -> None:
    created = client.post(
        "/api/v1/gate-controllers",
        json={
            "name": "  Garage Relay  ",
            "controller_type": "MOCK",
            "active": True,
            "pulse_ms": 500,
            "configuration": {},
        },
    )
    assert created.status_code == 201
    gate = created.json()
    assert gate["name"] == "Garage Relay"
    assert gate["healthy"] is True
    assert gate["runtime_state"] == "CLOSED"

    tested = client.post(f"/api/v1/gate-controllers/{gate['id']}/test-connection")
    assert tested.status_code == 200
    assert tested.json()["connected"] is True
    assert client.get("/api/v1/health").json()["components"]["gate"]["state"] == "HEALTHY"
    assert client.post(f"/api/v1/gate-controllers/{gate['id']}/open").status_code == 404

    assert client.delete(f"/api/v1/gate-controllers/{gate['id']}").status_code == 204


def test_access_rule_crud_validates_references_and_duplicates(client: TestClient) -> None:
    vehicle = client.post(
        "/api/v1/vehicles",
        json={"plate": "34ABC123", "owner": "Ada", "allowed_days": list(range(7))},
    ).json()
    camera = client.post(
        "/api/v1/cameras",
        json={
            "name": "Entrance",
            "camera_type": "RTSP",
            "stream_url": "rtsp://192.0.2.10/stream",
            "active": False,
        },
    ).json()
    gate = client.post(
        "/api/v1/gate-controllers",
        json={"name": "Gate A", "controller_type": "MOCK", "active": True},
    ).json()
    payload = {
        "name": "Entrance access",
        "vehicle_id": vehicle["id"],
        "camera_id": camera["id"],
        "gate_controller_id": gate["id"],
        "active": True,
    }

    created = client.post("/api/v1/access-rules", json=payload)
    assert created.status_code == 201
    rule = created.json()
    assert rule["camera_id"] == camera["id"]
    assert client.post("/api/v1/access-rules", json=payload).status_code == 409
    assert (
        client.post("/api/v1/access-rules", json={**payload, "vehicle_id": 9999}).status_code == 422
    )
    assert client.get("/api/v1/access-rules").json()[0]["id"] == rule["id"]
    assert client.delete(f"/api/v1/access-rules/{rule['id']}").status_code == 204


def test_gate_target_resolver_prefers_exact_camera_and_rejects_ambiguity(
    client: TestClient,
) -> None:
    vehicle = client.post(
        "/api/v1/vehicles",
        json={"plate": "06CD456", "owner": "Ece", "allowed_days": list(range(7))},
    ).json()
    camera = client.post(
        "/api/v1/cameras",
        json={
            "name": "Resolver Camera",
            "camera_type": "RTSP",
            "stream_url": "rtsp://192.0.2.20/stream",
            "active": False,
        },
    ).json()
    fallback_gate = client.post(
        "/api/v1/gate-controllers",
        json={"name": "Fallback Gate", "controller_type": "MOCK", "active": True},
    ).json()
    exact_gate = client.post(
        "/api/v1/gate-controllers",
        json={"name": "Exact Gate", "controller_type": "MOCK", "active": True},
    ).json()
    base = {"vehicle_id": vehicle["id"], "active": True}
    client.post(
        "/api/v1/access-rules",
        json={
            **base,
            "name": "Fallback",
            "camera_id": None,
            "gate_controller_id": fallback_gate["id"],
        },
    ).json()
    exact_rule = client.post(
        "/api/v1/access-rules",
        json={
            **base,
            "name": "Exact",
            "camera_id": camera["id"],
            "gate_controller_id": exact_gate["id"],
        },
    ).json()
    resolver = DatabaseGateTargetResolver(cast(FastAPI, client.app).state.session_factory)

    exact = resolver.resolve(vehicle["id"], camera["id"])
    assert exact.target is not None
    assert exact.target.gate_controller_id == exact_gate["id"]

    assert client.delete(f"/api/v1/access-rules/{exact_rule['id']}").status_code == 204
    fallback = resolver.resolve(vehicle["id"], camera["id"])
    assert fallback.target is not None
    assert fallback.target.gate_controller_id == fallback_gate["id"]

    client.post(
        "/api/v1/access-rules",
        json={
            **base,
            "name": "Second fallback",
            "camera_id": None,
            "gate_controller_id": exact_gate["id"],
        },
    )
    ambiguous = resolver.resolve(vehicle["id"], camera["id"])
    assert ambiguous.target is None
    assert ambiguous.outcome is GateOrchestrationOutcome.ACCESS_RULE_AMBIGUOUS
