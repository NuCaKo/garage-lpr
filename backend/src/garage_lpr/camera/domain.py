from dataclasses import dataclass, field
from enum import StrEnum


class CameraRuntimeState(StrEnum):
    STOPPED = "STOPPED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class NormalizedROI:
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0


@dataclass(frozen=True, slots=True)
class CameraRuntimeConfiguration:
    camera_id: int
    stream_url: str
    username: str | None
    password: str | None = field(repr=False)
    capture_fps_limit: float = 25.0
    requested_width: int | None = None
    requested_height: int | None = None
    connection_timeout_seconds: float = 5.0
    reconnect_schedule_seconds: tuple[float, ...] = (1, 2, 5, 10, 30)


@dataclass(frozen=True, slots=True)
class CameraRuntimeSnapshot:
    camera_id: int
    state: CameraRuntimeState
    detail: str
    frames_received: int
    frames_replaced: int
    last_frame_monotonic_ns: int | None


@dataclass(frozen=True, slots=True)
class CameraConnectionResult:
    connected: bool
    latency_ms: float
    width: int | None
    height: int | None
    fps: float | None
    detail: str
