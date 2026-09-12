from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from garage_lpr.access.authorization import AuthorizationResolver
from garage_lpr.access.cooldown import CooldownManager, CooldownStatus
from garage_lpr.access.status import AuthorizationStatus
from garage_lpr.detection.pipeline import DetectionPipelineResult
from garage_lpr.recognition.temporal import TemporalPlateValidator
from garage_lpr.recognition.tracker import IoUTracker


class RecognitionOutcome(StrEnum):
    AUTHORIZED_PENDING_GATE = "AUTHORIZED_PENDING_GATE"
    DENIED = "DENIED"
    MAINTENANCE_BLOCKED = "MAINTENANCE_BLOCKED"
    PLATE_COOLDOWN = "PLATE_COOLDOWN"
    GLOBAL_COOLDOWN = "GLOBAL_COOLDOWN"


@dataclass(frozen=True, slots=True)
class RecognitionDecision:
    camera_id: int
    track_id: int
    plate: str
    confidence: float
    confirmations: int
    authorization_status: AuthorizationStatus
    outcome: RecognitionOutcome
    vehicle_id: int | None
    reason: str
    retry_after_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class RecognitionBatch:
    decisions: tuple[RecognitionDecision, ...]
    active_tracks: int
    pending_validations: int


class RecognitionService:
    """Turns crop OCR candidates into bounded, fail-safe access decisions."""

    def __init__(
        self,
        tracker: IoUTracker,
        authorization: AuthorizationResolver,
        cooldown: CooldownManager,
        min_confidence: float,
        required_confirmations: int,
        confirmation_window_ms: int,
        maintenance_mode: bool = True,
    ) -> None:
        self._tracker = tracker
        self._authorization = authorization
        self._cooldown = cooldown
        self._min_confidence = min_confidence
        self._required_confirmations = required_confirmations
        self._confirmation_window_ms = confirmation_window_ms
        self._maintenance_mode = maintenance_mode
        self._validators: dict[tuple[int, int], TemporalPlateValidator] = {}
        self._completed_tracks: set[tuple[int, int]] = set()

    def process(
        self,
        result: DetectionPipelineResult,
        observed_ns: int,
        observed_at: datetime,
    ) -> RecognitionBatch:
        tracker_update = self._tracker.update(
            result.camera_id,
            tuple(candidate.box for candidate in result.candidates),
            observed_ns,
        )
        active_keys = {(result.camera_id, track_id) for track_id in tracker_update.active_track_ids}
        self._prune_camera_state(result.camera_id, active_keys)
        decisions: list[RecognitionDecision] = []
        for candidate, track_id in zip(result.candidates, tracker_update.track_ids, strict=True):
            key = (result.camera_id, track_id)
            if key in self._completed_tracks:
                continue
            if not candidate.valid_format or candidate.ocr_confidence < self._min_confidence:
                continue
            validator = self._validators.setdefault(key, self._new_validator())
            confirmation = validator.observe(
                candidate.normalized_text,
                candidate.ocr_confidence,
                observed_ns,
            )
            if confirmation is None:
                continue
            authorization = self._authorization.authorize(
                confirmation.plate,
                result.camera_id,
                observed_at,
            )
            outcome = RecognitionOutcome.DENIED
            retry_after = 0.0
            reason = authorization.reason
            if authorization.status is AuthorizationStatus.AUTHORIZED:
                if self._maintenance_mode:
                    outcome = RecognitionOutcome.MAINTENANCE_BLOCKED
                    reason = "MAINTENANCE_MODE"
                else:
                    cooldown = self._cooldown.check_and_reserve(confirmation.plate, observed_ns)
                    retry_after = cooldown.retry_after_seconds
                    if cooldown.status is CooldownStatus.ALLOWED:
                        outcome = RecognitionOutcome.AUTHORIZED_PENDING_GATE
                    elif cooldown.status is CooldownStatus.PLATE_COOLDOWN:
                        outcome = RecognitionOutcome.PLATE_COOLDOWN
                        reason = CooldownStatus.PLATE_COOLDOWN.value
                    else:
                        outcome = RecognitionOutcome.GLOBAL_COOLDOWN
                        reason = CooldownStatus.GLOBAL_COOLDOWN.value
            decisions.append(
                RecognitionDecision(
                    camera_id=result.camera_id,
                    track_id=track_id,
                    plate=confirmation.plate,
                    confidence=confirmation.confidence,
                    confirmations=confirmation.confirmations,
                    authorization_status=authorization.status,
                    outcome=outcome,
                    vehicle_id=authorization.vehicle_id,
                    reason=str(reason),
                    retry_after_seconds=retry_after,
                )
            )
            self._completed_tracks.add(key)
            self._validators.pop(key, None)
        return RecognitionBatch(
            decisions=tuple(decisions),
            active_tracks=len(active_keys),
            pending_validations=len(self._validators),
        )

    def _new_validator(self) -> TemporalPlateValidator:
        return TemporalPlateValidator(
            self._min_confidence,
            self._required_confirmations,
            self._confirmation_window_ms,
        )

    def _prune_camera_state(
        self,
        camera_id: int,
        active_keys: set[tuple[int, int]],
    ) -> None:
        for key in tuple(self._validators):
            if key[0] == camera_id and key not in active_keys:
                self._validators.pop(key, None)
        self._completed_tracks = {
            key for key in self._completed_tracks if key[0] != camera_id or key in active_keys
        }
