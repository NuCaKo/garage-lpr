from typing import Any

from garage_lpr.access.status import AuthorizationStatus
from garage_lpr.detection.pipeline import DetectionPipelineResult
from garage_lpr.events.domain import OperationalEvent
from garage_lpr.events.recorder import OperationalEventRecorder
from garage_lpr.events.types import EventType
from garage_lpr.gate.orchestration import GateOrchestrationOutcome, GateOrchestrationResult
from garage_lpr.recognition.service import RecognitionBatch, RecognitionDecision, RecognitionOutcome


class Publisher:
    def __init__(self) -> None:
        self.events: list[OperationalEvent] = []

    def publish(self, event: OperationalEvent) -> bool:
        self.events.append(event)
        return True


class Snapshots:
    def __init__(self) -> None:
        self.calls = 0

    def capture(self, event_id: str, image: Any) -> str | None:
        self.calls += 1
        return f"2026/09/11/{event_id}.jpg"


def _decision(outcome: RecognitionOutcome) -> RecognitionDecision:
    return RecognitionDecision(
        camera_id=2,
        track_id=8,
        plate="34ABC123",
        confidence=0.95,
        confirmations=3,
        authorization_status=(
            AuthorizationStatus.AUTHORIZED
            if outcome is RecognitionOutcome.AUTHORIZED_PENDING_GATE
            else AuthorizationStatus.UNAUTHORIZED
        ),
        outcome=outcome,
        vehicle_id=4 if outcome is RecognitionOutcome.AUTHORIZED_PENDING_GATE else None,
        reason=outcome.value,
    )


def _pipeline_result() -> DetectionPipelineResult:
    return DetectionPipelineResult(2, 1, (), 1, 0, 2.0, 0.0, 2.0)


def test_recorder_rate_limits_detection_and_snapshots_denial() -> None:
    publisher = Publisher()
    snapshots = Snapshots()
    recorder = OperationalEventRecorder(publisher, snapshots, 5.0)
    batch = RecognitionBatch((_decision(RecognitionOutcome.DENIED),), 1, 0)

    recorder.record(_pipeline_result(), batch, (), object(), 1_000_000_000)
    recorder.record(_pipeline_result(), RecognitionBatch((), 1, 0), (), object(), 2_000_000_000)

    assert [event.event_type for event in publisher.events] == [
        EventType.PLATE_DETECTED,
        EventType.PLATE_RECOGNIZED,
        EventType.ACCESS_DENIED,
    ]
    assert snapshots.calls == 1
    assert "snapshot_path" in publisher.events[-1].metadata


def test_recorder_creates_gate_and_access_success_audit() -> None:
    publisher = Publisher()
    snapshots = Snapshots()
    recorder = OperationalEventRecorder(publisher, snapshots, 5.0)
    gate = GateOrchestrationResult(
        camera_id=2,
        vehicle_id=4,
        plate="34ABC123",
        outcome=GateOrchestrationOutcome.GATE_OPEN_SUCCESS,
        detail="OPENED",
        access_rule_id=5,
        gate_controller_id=6,
    )

    recorder.record(
        _pipeline_result(),
        RecognitionBatch((_decision(RecognitionOutcome.AUTHORIZED_PENDING_GATE),), 1, 0),
        (gate,),
        object(),
        1_000_000_000,
    )

    assert [event.event_type for event in publisher.events] == [
        EventType.PLATE_DETECTED,
        EventType.PLATE_RECOGNIZED,
        EventType.GATE_OPEN_REQUESTED,
        EventType.GATE_OPEN_SUCCESS,
        EventType.ACCESS_GRANTED,
    ]
    assert snapshots.calls == 1
