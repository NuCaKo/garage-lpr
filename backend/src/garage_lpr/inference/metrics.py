from threading import Lock
from time import monotonic

from garage_lpr.detection.pipeline import DetectionPipelineResult
from garage_lpr.gate.orchestration import (
    GateOrchestrationOutcome,
    GateOrchestrationResult,
)
from garage_lpr.inference.domain import (
    InferenceRuntimeSnapshot,
    InferenceRuntimeState,
)
from garage_lpr.recognition.service import RecognitionBatch, RecognitionOutcome

EWMA_ALPHA = 0.2


class InferenceMetrics:
    """Stores only scalar counters and EWMAs; no unbounded sample history."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._frames_sampled = 0
        self._plates_detected = 0
        self._ocr_calls = 0
        self._valid_plates = 0
        self._last_plate: str | None = None
        self._effective_fps = 0.0
        self._detection_latency = 0.0
        self._ocr_latency = 0.0
        self._total_latency = 0.0
        self._last_processed_monotonic: float | None = None
        self._active_tracks = 0
        self._pending_validations = 0
        self._recognized_plates = 0
        self._access_ready = 0
        self._access_denied = 0
        self._cooldown_suppressed = 0
        self._last_decision_plate: str | None = None
        self._last_authorization_status: str | None = None
        self._last_recognition_outcome: str | None = None
        self._gate_open_success = 0
        self._gate_open_failed = 0
        self._simulated_gate_open = 0
        self._last_gate_outcome: str | None = None

    def record(self, result: DetectionPipelineResult) -> None:
        now = monotonic()
        with self._lock:
            self._frames_sampled += 1
            self._plates_detected += result.detection_count
            self._ocr_calls += result.ocr_calls
            valid = [candidate for candidate in result.candidates if candidate.valid_format]
            self._valid_plates += len(valid)
            if result.candidates:
                self._last_plate = result.candidates[0].normalized_text or None
            if self._last_processed_monotonic is not None:
                interval = now - self._last_processed_monotonic
                if interval > 0:
                    self._effective_fps = _ewma(self._effective_fps, 1.0 / interval)
            self._last_processed_monotonic = now
            self._detection_latency = _ewma(self._detection_latency, result.detection_latency_ms)
            average_ocr = (
                result.total_ocr_latency_ms / result.ocr_calls if result.ocr_calls else 0.0
            )
            self._ocr_latency = _ewma(self._ocr_latency, average_ocr)
            self._total_latency = _ewma(self._total_latency, result.total_latency_ms)

    def record_recognition(self, batch: RecognitionBatch) -> None:
        with self._lock:
            self._active_tracks = batch.active_tracks
            self._pending_validations = batch.pending_validations
            self._recognized_plates += len(batch.decisions)
            for decision in batch.decisions:
                if decision.outcome is RecognitionOutcome.AUTHORIZED_PENDING_GATE:
                    self._access_ready += 1
                elif decision.outcome in {
                    RecognitionOutcome.PLATE_COOLDOWN,
                    RecognitionOutcome.GLOBAL_COOLDOWN,
                }:
                    self._cooldown_suppressed += 1
                else:
                    self._access_denied += 1
                self._last_decision_plate = decision.plate
                self._last_authorization_status = decision.authorization_status
                self._last_recognition_outcome = decision.outcome

    def record_gate(self, results: tuple[GateOrchestrationResult, ...]) -> None:
        with self._lock:
            for result in results:
                if result.outcome is GateOrchestrationOutcome.GATE_OPEN_SUCCESS:
                    self._gate_open_success += 1
                elif result.outcome is GateOrchestrationOutcome.SIMULATED_GATE_OPEN:
                    self._simulated_gate_open += 1
                else:
                    self._gate_open_failed += 1
                self._last_gate_outcome = result.outcome

    def snapshot(
        self,
        state: InferenceRuntimeState,
        detail: str,
        detector_provider: str | None,
        ocr_provider: str | None,
        active_camera_count: int,
    ) -> InferenceRuntimeSnapshot:
        with self._lock:
            return InferenceRuntimeSnapshot(
                state=state,
                detail=detail,
                detector_provider=detector_provider,
                ocr_provider=ocr_provider,
                active_camera_count=active_camera_count,
                frames_sampled=self._frames_sampled,
                plates_detected=self._plates_detected,
                ocr_calls=self._ocr_calls,
                valid_plates=self._valid_plates,
                last_plate=self._last_plate,
                effective_detection_fps=round(self._effective_fps, 2),
                detection_latency_ms=round(self._detection_latency, 2),
                ocr_latency_ms=round(self._ocr_latency, 2),
                total_latency_ms=round(self._total_latency, 2),
                active_tracks=self._active_tracks,
                pending_validations=self._pending_validations,
                recognized_plates=self._recognized_plates,
                access_ready=self._access_ready,
                access_denied=self._access_denied,
                cooldown_suppressed=self._cooldown_suppressed,
                last_decision_plate=self._last_decision_plate,
                last_authorization_status=self._last_authorization_status,
                last_recognition_outcome=self._last_recognition_outcome,
                gate_open_success=self._gate_open_success,
                gate_open_failed=self._gate_open_failed,
                simulated_gate_open=self._simulated_gate_open,
                last_gate_outcome=self._last_gate_outcome,
            )


def _ewma(current: float, sample: float) -> float:
    return sample if current == 0 else EWMA_ALPHA * sample + (1 - EWMA_ALPHA) * current
