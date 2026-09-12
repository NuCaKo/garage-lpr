from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from garage_lpr.database.models import RecognitionEvent
from garage_lpr.events.domain import OperationalEvent

_INTERNAL_METADATA_KEYS = {
    "_event_id",
    "_vehicle_id",
    "_gate_controller_id",
    "_reason",
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class EventRead(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str
    camera_id: int | None
    plate: str | None
    confidence: float | None
    status: str
    vehicle_id: int | None
    gate_controller_id: int | None
    reason: str | None
    metadata: dict[str, Any]

    @classmethod
    def from_model(cls, event: RecognitionEvent) -> "EventRead":
        metadata = dict(event.metadata_json or {})
        event_id = str(metadata.get("_event_id") or f"db-{event.id}")
        values = {
            "vehicle_id": metadata.get("_vehicle_id"),
            "gate_controller_id": metadata.get("_gate_controller_id"),
            "reason": metadata.get("_reason"),
        }
        public_metadata = {
            key: value for key, value in metadata.items() if key not in _INTERNAL_METADATA_KEYS
        }
        return cls(
            event_id=event_id,
            timestamp=_as_utc(event.timestamp),
            event_type=event.event_type,
            camera_id=event.camera_id,
            plate=event.plate,
            confidence=event.confidence,
            status=event.status,
            metadata=public_metadata,
            **values,
        )

    @classmethod
    def from_domain(cls, event: OperationalEvent) -> "EventRead":
        return cls(
            event_id=event.event_id,
            timestamp=_as_utc(event.timestamp),
            event_type=event.event_type.value,
            camera_id=event.camera_id,
            plate=event.plate,
            confidence=event.confidence,
            status=event.status,
            vehicle_id=event.vehicle_id,
            gate_controller_id=event.gate_controller_id,
            reason=event.reason,
            metadata=event.metadata,
        )


class EventListRead(BaseModel):
    items: list[EventRead]
    total: int
    limit: int
    offset: int
