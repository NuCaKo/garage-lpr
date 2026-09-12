from dataclasses import replace
from typing import Any, Protocol

from garage_lpr.detection.pipeline import DetectionPipelineResult
from garage_lpr.events.domain import OperationalEvent
from garage_lpr.events.types import EventType
from garage_lpr.gate.orchestration import GateOrchestrationOutcome, GateOrchestrationResult
from garage_lpr.recognition.service import RecognitionBatch, RecognitionOutcome


class EventPublisher(Protocol):
    def publish(self, event: OperationalEvent) -> bool: ...


class SnapshotCapture(Protocol):
    def capture(self, event_id: str, image: Any) -> str | None: ...


class OperationalEventRecorder:
    """Maps pipeline outcomes to a stable, auditable event vocabulary."""

    def __init__(
        self,
        publisher: EventPublisher,
        snapshot_service: SnapshotCapture,
        detection_event_interval_seconds: float,
    ) -> None:
        self._publisher = publisher
        self._snapshots = snapshot_service
        self._detection_interval_ns = int(detection_event_interval_seconds * 1_000_000_000)
        self._last_detection_ns: dict[int, int] = {}

    def record(
        self,
        result: DetectionPipelineResult,
        batch: RecognitionBatch,
        gate_results: tuple[GateOrchestrationResult, ...],
        image: Any,
        observed_ns: int,
    ) -> None:
        self._record_detection(result, observed_ns)
        gate_keys = {(item.camera_id, item.plate) for item in gate_results}
        for decision in batch.decisions:
            self._publisher.publish(
                OperationalEvent.create(
                    EventType.PLATE_RECOGNIZED,
                    decision.outcome.value,
                    camera_id=decision.camera_id,
                    plate=decision.plate,
                    confidence=decision.confidence,
                    vehicle_id=decision.vehicle_id,
                    reason=decision.reason,
                    metadata={
                        "track_id": decision.track_id,
                        "confirmations": decision.confirmations,
                        "authorization_status": decision.authorization_status.value,
                    },
                )
            )
            if (
                (decision.camera_id, decision.plate) not in gate_keys
                and decision.outcome is not RecognitionOutcome.AUTHORIZED_PENDING_GATE
            ):
                self._publish_access(
                    EventType.ACCESS_DENIED,
                    decision.outcome.value,
                    image,
                    camera_id=decision.camera_id,
                    plate=decision.plate,
                    confidence=decision.confidence,
                    vehicle_id=decision.vehicle_id,
                    reason=decision.reason,
                )
        decisions_by_key = {
            (decision.camera_id, decision.plate): decision for decision in batch.decisions
        }
        for gate_result in gate_results:
            gate_decision = decisions_by_key.get((gate_result.camera_id, gate_result.plate))
            self._record_gate(
                gate_result,
                image,
                confidence=gate_decision.confidence if gate_decision else None,
            )

    def record_error(self, camera_id: int, error_type: str, image: Any) -> None:
        event = OperationalEvent.create(
            EventType.RECOGNITION_ERROR,
            "ERROR",
            camera_id=camera_id,
            reason=error_type,
        )
        self._publisher.publish(self._with_snapshot(event, image))

    def _record_detection(self, result: DetectionPipelineResult, observed_ns: int) -> None:
        if result.detection_count == 0:
            return
        previous = self._last_detection_ns.get(result.camera_id)
        if previous is not None and observed_ns - previous < self._detection_interval_ns:
            return
        self._last_detection_ns[result.camera_id] = observed_ns
        self._publisher.publish(
            OperationalEvent.create(
                EventType.PLATE_DETECTED,
                "DETECTED",
                camera_id=result.camera_id,
                metadata={"detection_count": result.detection_count},
            )
        )

    def _record_gate(
        self,
        result: GateOrchestrationResult,
        image: Any,
        *,
        confidence: float | None,
    ) -> None:
        if result.outcome in {
            GateOrchestrationOutcome.GATE_OPEN_SUCCESS,
            GateOrchestrationOutcome.GATE_OPEN_FAILED,
        }:
            self._publisher.publish(
                self._gate_event(EventType.GATE_OPEN_REQUESTED, result, confidence)
            )
        if result.outcome is GateOrchestrationOutcome.GATE_OPEN_SUCCESS:
            gate_type = EventType.GATE_OPEN_SUCCESS
            access_type = EventType.ACCESS_GRANTED
        elif result.outcome is GateOrchestrationOutcome.SIMULATED_GATE_OPEN:
            gate_type = EventType.SIMULATED_GATE_OPEN
            access_type = EventType.ACCESS_GRANTED
        else:
            gate_type = EventType.GATE_OPEN_FAILED
            access_type = EventType.ACCESS_DENIED
        self._publisher.publish(self._gate_event(gate_type, result, confidence))
        self._publish_access(
            access_type,
            result.outcome.value,
            image,
            camera_id=result.camera_id,
            plate=result.plate,
            confidence=confidence,
            vehicle_id=result.vehicle_id,
            gate_controller_id=result.gate_controller_id,
            reason=result.detail,
            metadata={"access_rule_id": result.access_rule_id},
        )

    def _gate_event(
        self,
        event_type: EventType,
        result: GateOrchestrationResult,
        confidence: float | None,
    ) -> OperationalEvent:
        return OperationalEvent.create(
            event_type,
            result.outcome.value,
            camera_id=result.camera_id,
            plate=result.plate,
            confidence=confidence,
            vehicle_id=result.vehicle_id,
            gate_controller_id=result.gate_controller_id,
            reason=result.detail,
            metadata={"access_rule_id": result.access_rule_id},
        )

    def _publish_access(
        self,
        event_type: EventType,
        status: str,
        image: Any,
        **values: Any,
    ) -> None:
        event = OperationalEvent.create(event_type, status, **values)
        self._publisher.publish(self._with_snapshot(event, image))

    def _with_snapshot(self, event: OperationalEvent, image: Any) -> OperationalEvent:
        snapshot_path = self._snapshots.capture(event.event_id, image)
        if snapshot_path is None:
            return event
        return replace(event, metadata={**event.metadata, "snapshot_path": snapshot_path})
