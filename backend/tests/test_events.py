from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from garage_lpr.database.models import AccessEvent, RecognitionEvent
from garage_lpr.database.repositories.events import EventRepository
from garage_lpr.events.broker import LiveEventBroker
from garage_lpr.events.domain import OperationalEvent
from garage_lpr.events.service import EventService
from garage_lpr.events.types import EventType


def _wait_for_event(client: TestClient, event_id: str) -> dict[str, object]:
    deadline = monotonic() + 2.0
    while monotonic() < deadline:
        response = client.get("/api/v1/events", params={"limit": 100})
        for item in response.json()["items"]:
            if item["event_id"] == event_id:
                return item
        sleep(0.01)
    raise AssertionError(f"Event {event_id} was not persisted")


def _app(client: TestClient) -> FastAPI:
    return cast(FastAPI, client.app)


def test_event_service_persists_and_filters_access_audit(client: TestClient) -> None:
    event = OperationalEvent.create(
        EventType.ACCESS_GRANTED,
        "AUTHORIZED",
        camera_id=None,
        plate="34ABC123",
        confidence=0.96,
        vehicle_id=None,
        gate_controller_id=None,
        reason="TEST_GRANTED",
        metadata={"source": "test"},
    )

    assert _app(client).state.event_service.publish(event)
    persisted = _wait_for_event(client, event.event_id)
    filtered = client.get(
        "/api/v1/events",
        params={"event_type": "access_granted", "plate": "34-abc-123"},
    )
    session = _app(client).state.session_factory()
    try:
        access_count = session.scalar(select(func.count(AccessEvent.id)))
    finally:
        session.close()

    assert persisted["status"] == "AUTHORIZED"
    assert persisted["reason"] == "TEST_GRANTED"
    assert persisted["metadata"] == {"source": "test"}
    assert filtered.status_code == 200
    assert any(item["event_id"] == event.event_id for item in filtered.json()["items"])
    assert access_count == 1


def test_websocket_receives_only_persisted_events(client: TestClient) -> None:
    event = OperationalEvent.create(EventType.SYSTEM_STARTED, "TEST")

    with client.websocket_connect("/api/v1/events/live") as websocket:
        assert _app(client).state.event_service.publish(event)
        payload = websocket.receive_json()

    assert payload["event_id"] == event.event_id
    assert payload["event_type"] == "system_started"
    assert _wait_for_event(client, event.event_id)["status"] == "TEST"


def test_resource_metrics_and_event_health_are_exposed(client: TestClient) -> None:
    resources = client.get("/api/v1/metrics/resources")
    health = client.get("/api/v1/health")

    assert resources.status_code == 200
    assert resources.json()["process_rss_bytes"] > 0
    assert resources.json()["system_ram_total_bytes"] > 0
    assert resources.json()["process_thread_count"] > 0
    assert health.json()["components"]["events"]["state"] == "HEALTHY"
    assert health.json()["components"]["storage"]["state"] == "HEALTHY"
    assert health.json()["components"]["disk"]["state"] in {
        "HEALTHY",
        "DEGRADED",
        "UNHEALTHY",
    }


def test_event_worker_survives_session_factory_failure() -> None:
    def unavailable_session() -> Session:
        raise RuntimeError("database unavailable")

    service = EventService(unavailable_session, LiveEventBroker(), queue_capacity=4)
    service.start()
    try:
        assert service.publish(OperationalEvent.create(EventType.SYSTEM_STARTED, "TEST"))
        deadline = monotonic() + 1.0
        while service.snapshot().failed == 0 and monotonic() < deadline:
            sleep(0.01)

        snapshot = service.snapshot()
        assert snapshot.failed == 1
        assert snapshot.running
    finally:
        service.shutdown()


def test_event_repository_prunes_old_recognition_and_access_rows(client: TestClient) -> None:
    session = _app(client).state.session_factory()
    repository = EventRepository(session)
    try:
        old_event = OperationalEvent(
            event_id="old-access-event",
            timestamp=datetime.now(UTC) - timedelta(days=10),
            event_type=EventType.ACCESS_DENIED,
            status="UNAUTHORIZED",
        )
        recent_event = OperationalEvent.create(EventType.PLATE_RECOGNIZED, "RECOGNIZED")
        repository.persist(old_event)
        repository.persist(recent_event)

        pruned = repository.prune_older_than(datetime.now(UTC) - timedelta(days=5))
        recognition_ids = set(session.scalars(select(RecognitionEvent.id)))
        remaining_access = int(session.scalar(select(func.count(AccessEvent.id))) or 0)
    finally:
        session.close()

    assert pruned == 2
    assert len(recognition_ids) >= 1
    assert remaining_access == 0


def test_runtime_settings_update_reconfigures_event_retention(client: TestClient) -> None:
    settings = client.get("/api/v1/system-settings").json()
    settings["event_retention_days"] = 45

    response = client.put("/api/v1/system-settings", json=settings)

    assert response.status_code == 200
    assert response.json()["event_retention_days"] == 45
    assert _app(client).state.event_service.snapshot().retention_days == 45
