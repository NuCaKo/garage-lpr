from dataclasses import dataclass
from enum import StrEnum

from garage_lpr.camera.domain import NormalizedROI


class InferenceRuntimeState(StrEnum):
    STOPPED = "STOPPED"
    CONFIGURATION_REQUIRED = "CONFIGURATION_REQUIRED"
    READY = "READY"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class InferenceCameraConfiguration:
    camera_id: int
    active: bool
    detection_fps: float
    roi: NormalizedROI


@dataclass(frozen=True, slots=True)
class InferenceRuntimeSnapshot:
    state: InferenceRuntimeState
    detail: str
    detector_provider: str | None
    ocr_provider: str | None
    active_camera_count: int
    frames_sampled: int
    plates_detected: int
    ocr_calls: int
    valid_plates: int
    last_plate: str | None
    effective_detection_fps: float
    detection_latency_ms: float
    ocr_latency_ms: float
    total_latency_ms: float
    active_tracks: int = 0
    pending_validations: int = 0
    recognized_plates: int = 0
    access_ready: int = 0
    access_denied: int = 0
    cooldown_suppressed: int = 0
    last_decision_plate: str | None = None
    last_authorization_status: str | None = None
    last_recognition_outcome: str | None = None
    gate_open_success: int = 0
    gate_open_failed: int = 0
    simulated_gate_open: int = 0
    last_gate_outcome: str | None = None
    frame_buffer_capacity: int = 1
    queue_size: int = 0
