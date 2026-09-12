from pydantic import BaseModel


class InferenceMetricsRead(BaseModel):
    state: str
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
    active_tracks: int
    pending_validations: int
    recognized_plates: int
    access_ready: int
    access_denied: int
    cooldown_suppressed: int
    last_decision_plate: str | None
    last_authorization_status: str | None
    last_recognition_outcome: str | None
    gate_open_success: int
    gate_open_failed: int
    simulated_gate_open: int
    last_gate_outcome: str | None
    frame_buffer_capacity: int
    queue_size: int


class ResourceMetricsRead(BaseModel):
    system_cpu_percent: float
    system_ram_percent: float
    system_ram_used_bytes: int
    system_ram_total_bytes: int
    process_cpu_percent: float
    process_rss_bytes: int
    process_thread_count: int
    disk_percent: float
    disk_free_bytes: int
    uptime_seconds: float
