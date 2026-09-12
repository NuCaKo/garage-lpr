from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from garage_lpr.events.types import EventType


@dataclass(frozen=True, slots=True)
class OperationalEvent:
    event_id: str
    timestamp: datetime
    event_type: EventType
    status: str
    camera_id: int | None = None
    plate: str | None = None
    confidence: float | None = None
    vehicle_id: int | None = None
    gate_controller_id: int | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: EventType,
        status: str,
        *,
        camera_id: int | None = None,
        plate: str | None = None,
        confidence: float | None = None,
        vehicle_id: int | None = None,
        gate_controller_id: int | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "OperationalEvent":
        return cls(
            event_id=uuid4().hex,
            timestamp=datetime.now(UTC),
            event_type=event_type,
            status=status,
            camera_id=camera_id,
            plate=plate,
            confidence=confidence,
            vehicle_id=vehicle_id,
            gate_controller_id=gate_controller_id,
            reason=reason,
            metadata=metadata or {},
        )


@dataclass(frozen=True, slots=True)
class EventServiceSnapshot:
    running: bool
    queue_size: int
    queue_capacity: int
    persisted: int
    pruned: int
    dropped: int
    failed: int
    retention_days: int
    subscriber_count: int
    last_error: str | None
