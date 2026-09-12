from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from garage_lpr.database.models import AccessEvent, RecognitionEvent
from garage_lpr.events.domain import OperationalEvent
from garage_lpr.events.types import EventType

ACCESS_AUDIT_TYPES = {
    EventType.ACCESS_GRANTED,
    EventType.ACCESS_DENIED,
    EventType.GATE_OPEN_REQUESTED,
    EventType.GATE_OPEN_SUCCESS,
    EventType.GATE_OPEN_FAILED,
    EventType.SIMULATED_GATE_OPEN,
}


class EventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def persist(self, event: OperationalEvent) -> RecognitionEvent:
        metadata = {
            **event.metadata,
            "_event_id": event.event_id,
            "_vehicle_id": event.vehicle_id,
            "_gate_controller_id": event.gate_controller_id,
            "_reason": event.reason,
        }
        recognition = RecognitionEvent(
            timestamp=event.timestamp,
            event_type=event.event_type.value,
            camera_id=event.camera_id,
            plate=event.plate,
            confidence=event.confidence,
            status=event.status,
            metadata_json=metadata,
        )
        self._session.add(recognition)
        self._session.flush()
        if event.event_type in ACCESS_AUDIT_TYPES:
            self._session.add(
                AccessEvent(
                    timestamp=event.timestamp,
                    recognition_event_id=recognition.id,
                    vehicle_id=event.vehicle_id,
                    gate_controller_id=event.gate_controller_id,
                    plate=event.plate,
                    status=event.status,
                    reason=event.reason,
                    metadata_json=metadata,
                )
            )
        self._session.commit()
        self._session.refresh(recognition)
        return recognition

    def list_recent(
        self,
        *,
        limit: int,
        offset: int,
        event_type: EventType | None = None,
        camera_id: int | None = None,
        plate: str | None = None,
        status: str | None = None,
    ) -> tuple[Sequence[RecognitionEvent], int]:
        conditions = []
        if event_type is not None:
            conditions.append(RecognitionEvent.event_type == event_type.value)
        if camera_id is not None:
            conditions.append(RecognitionEvent.camera_id == camera_id)
        if plate is not None:
            conditions.append(RecognitionEvent.plate == plate)
        if status is not None:
            conditions.append(RecognitionEvent.status == status)
        statement = (
            select(RecognitionEvent)
            .where(*conditions)
            .order_by(RecognitionEvent.timestamp.desc(), RecognitionEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
        total_statement = select(func.count(RecognitionEvent.id)).where(*conditions)
        return tuple(self._session.scalars(statement)), int(
            self._session.scalar(total_statement) or 0
        )

    def prune_older_than(self, cutoff: datetime) -> int:
        """Delete old audit rows in dependency order and return the total count."""
        access_result = self._session.execute(
            delete(AccessEvent).where(AccessEvent.timestamp < cutoff)
        )
        recognition_result = self._session.execute(
            delete(RecognitionEvent).where(RecognitionEvent.timestamp < cutoff)
        )
        self._session.commit()
        access_count = int(getattr(access_result, "rowcount", 0) or 0)
        recognition_count = int(getattr(recognition_result, "rowcount", 0) or 0)
        return access_count + recognition_count
