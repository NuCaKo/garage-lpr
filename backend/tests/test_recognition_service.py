from datetime import UTC, datetime

from garage_lpr.access.authorization import AuthorizationDecision
from garage_lpr.access.cooldown import CooldownManager
from garage_lpr.access.status import AuthorizationStatus
from garage_lpr.detection.contracts import BoundingBox
from garage_lpr.detection.pipeline import (
    DetectionPipelineResult,
    PlateRecognitionCandidate,
)
from garage_lpr.recognition.service import RecognitionOutcome, RecognitionService
from garage_lpr.recognition.tracker import IoUTracker


class Authorization:
    def __init__(self, status: AuthorizationStatus) -> None:
        self.status = status
        self.calls = 0

    def authorize(self, plate: str, camera_id: int, observed_at: datetime) -> AuthorizationDecision:
        self.calls += 1
        return AuthorizationDecision(
            self.status,
            7 if self.status is AuthorizationStatus.AUTHORIZED else None,
            self.status.value,
        )


def _result(sequence: int, plate: str = "34ABC123") -> DetectionPipelineResult:
    candidate = PlateRecognitionCandidate(
        box=BoundingBox(10, 10, 110, 60),
        detection_confidence=0.95,
        raw_text=plate,
        normalized_text=plate,
        ocr_confidence=0.95,
        valid_format=True,
        normalization_corrections=(),
        ocr_processing_time_ms=2,
    )
    return DetectionPipelineResult(1, sequence, (candidate,), 1, 1, 3, 2, 5)


def test_recognition_authorizes_only_after_temporal_confirmation_and_once_per_track() -> None:
    authorization = Authorization(AuthorizationStatus.AUTHORIZED)
    service = RecognitionService(
        IoUTracker(max_tracks=8),
        authorization,
        CooldownManager(20, 3),
        min_confidence=0.85,
        required_confirmations=3,
        confirmation_window_ms=2000,
        maintenance_mode=False,
    )
    observed_at = datetime(2026, 9, 11, tzinfo=UTC)

    assert not service.process(_result(1), 0, observed_at).decisions
    assert not service.process(_result(2), 200_000_000, observed_at).decisions
    decision = service.process(_result(3), 400_000_000, observed_at).decisions[0]
    repeated = service.process(_result(4), 600_000_000, observed_at)

    assert decision.outcome is RecognitionOutcome.AUTHORIZED_PENDING_GATE
    assert decision.confirmations == 3
    assert authorization.calls == 1
    assert not repeated.decisions


def test_recognition_maintenance_mode_never_reserves_gate_ready_outcome() -> None:
    service = RecognitionService(
        IoUTracker(max_tracks=10),
        Authorization(AuthorizationStatus.AUTHORIZED),
        CooldownManager(20, 3),
        min_confidence=0.85,
        required_confirmations=2,
        confirmation_window_ms=2000,
        maintenance_mode=True,
    )
    observed_at = datetime(2026, 9, 11, tzinfo=UTC)

    service.process(_result(1), 0, observed_at)
    decision = service.process(_result(2), 200_000_000, observed_at).decisions[0]

    assert decision.outcome is RecognitionOutcome.MAINTENANCE_BLOCKED
    assert decision.reason == "MAINTENANCE_MODE"
