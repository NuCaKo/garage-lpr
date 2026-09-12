from datetime import datetime
from typing import Self
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from garage_lpr.camera.domain import CameraConnectionResult, CameraRuntimeSnapshot
from garage_lpr.database.models import Camera


class NormalizedROISchema(BaseModel):
    x: float = Field(default=0.0, ge=0.0, le=1.0)
    y: float = Field(default=0.0, ge=0.0, le=1.0)
    width: float = Field(default=1.0, gt=0.0, le=1.0)
    height: float = Field(default=1.0, gt=0.0, le=1.0)

    @model_validator(mode="after")
    def contained_in_frame(self) -> Self:
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("ROI must stay within normalized frame bounds")
        return self


class CameraWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    camera_type: str = Field(default="RTSP", pattern="^RTSP$")
    stream_url: str = Field(min_length=8, max_length=2048)
    username: str | None = Field(default=None, max_length=120)
    password: SecretStr | None = None
    capture_fps_limit: float = Field(default=25.0, ge=1.0, le=60.0)
    detection_fps: float = Field(default=5.0, ge=0.5, le=15.0)
    requested_width: int | None = Field(default=None, ge=160, le=7680)
    requested_height: int | None = Field(default=None, ge=120, le=4320)
    roi: NormalizedROISchema = Field(default_factory=NormalizedROISchema)
    active: bool = False
    connection_timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)
    reconnect_schedule_seconds: list[int] = Field(
        default_factory=lambda: [1, 2, 5, 10, 30], min_length=1, max_length=10
    )

    @field_validator("name", "username")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("stream_url")
    @classmethod
    def validate_rtsp_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"rtsp", "rtsps"} or not parsed.hostname:
            raise ValueError("A valid rtsp:// or rtsps:// URL is required")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials must use the separate username and password fields")
        return value

    @field_validator("reconnect_schedule_seconds")
    @classmethod
    def validate_backoff(cls, values: list[int]) -> list[int]:
        if any(value < 1 or value > 300 for value in values):
            raise ValueError("Reconnect delays must be between 1 and 300 seconds")
        if values != sorted(values):
            raise ValueError("Reconnect delays must be non-decreasing")
        return values

    @model_validator(mode="after")
    def validate_relationships(self) -> Self:
        if bool(self.requested_width) != bool(self.requested_height):
            raise ValueError("Resolution width and height must be set together")
        if self.detection_fps > self.capture_fps_limit:
            raise ValueError("Detection FPS cannot exceed capture FPS limit")
        return self

    def persistence_values(self) -> dict[str, object]:
        return self.model_dump(
            exclude={"password"},
            mode="json",
        )


class CameraCreate(CameraWrite):
    pass


class CameraUpdate(CameraWrite):
    clear_password: bool = False

    def persistence_values(self) -> dict[str, object]:
        return self.model_dump(
            exclude={"password", "clear_password"},
            mode="json",
        )


class CameraRead(BaseModel):
    id: int
    name: str
    camera_type: str
    stream_url: str
    username: str | None
    has_password: bool
    capture_fps_limit: float
    detection_fps: float
    requested_width: int | None
    requested_height: int | None
    roi: NormalizedROISchema
    active: bool
    connection_timeout_seconds: float
    reconnect_schedule_seconds: list[int]
    runtime_state: str
    runtime_detail: str
    frames_received: int
    frames_replaced: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_camera(cls, camera: Camera, runtime: CameraRuntimeSnapshot) -> "CameraRead":
        return cls(
            id=camera.id,
            name=camera.name,
            camera_type=camera.camera_type,
            stream_url=camera.stream_url,
            username=camera.username,
            has_password=camera.credentials_ciphertext is not None,
            capture_fps_limit=camera.capture_fps_limit,
            detection_fps=camera.detection_fps,
            requested_width=camera.requested_width,
            requested_height=camera.requested_height,
            roi=NormalizedROISchema.model_validate(camera.roi or {}),
            active=camera.active,
            connection_timeout_seconds=camera.connection_timeout_seconds,
            reconnect_schedule_seconds=camera.reconnect_schedule_seconds,
            runtime_state=runtime.state,
            runtime_detail=runtime.detail,
            frames_received=runtime.frames_received,
            frames_replaced=runtime.frames_replaced,
            created_at=camera.created_at,
            updated_at=camera.updated_at,
        )


class CameraConnectionRead(BaseModel):
    connected: bool
    latency_ms: float
    resolution: str | None
    fps: float | None
    detail: str

    @classmethod
    def from_result(cls, result: CameraConnectionResult) -> "CameraConnectionRead":
        resolution = (
            f"{result.width}×{result.height}"
            if result.width is not None and result.height is not None
            else None
        )
        return cls(
            connected=result.connected,
            latency_ms=result.latency_ms,
            resolution=resolution,
            fps=result.fps,
            detail=result.detail,
        )
