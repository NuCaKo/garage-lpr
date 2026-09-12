import os
import sys
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def repository_root() -> Path:
    """Return the read-only application resource root.

    PyInstaller exposes bundled data below ``sys._MEIPASS``. Source and editable
    installs continue to resolve resources from the repository root.
    """
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root).resolve()
    return Path(__file__).resolve().parents[4]


def runtime_root() -> Path:
    """Return the writable root for database, secrets, logs, and snapshots."""
    configured = os.environ.get("GARAGE_LPR_RUNTIME_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    if getattr(sys, "frozen", False) and os.name == "nt":
        program_data = os.environ.get("PROGRAMDATA")
        if program_data:
            return (Path(program_data) / "GarageLPR").resolve()
    return repository_root()


class BootstrapSettings(BaseSettings):
    """Immutable process bootstrap values loaded before the database is available."""

    model_config = SettingsConfigDict(
        env_file=runtime_root() / ".env",
        env_prefix="GARAGE_LPR_",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "Garage LPR"
    environment: Literal["development", "test", "production"] = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)
    database_url: str = f"sqlite:///{runtime_root() / 'runtime/data/garage_lpr.db'}"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_directory: Path = runtime_root() / "runtime/logs"
    snapshot_directory: Path = runtime_root() / "runtime/snapshots"
    frontend_dist_directory: Path = repository_root() / "frontend/dist"
    secret_key_path: Path = runtime_root() / "runtime/data/camera-secrets.key"
    log_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    log_backup_count: int = Field(default=5, ge=1, le=100)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    auto_migrate: bool = True
    max_active_cameras: int = Field(default=1, ge=1, le=32)
    preview_jpeg_quality: int = Field(default=75, ge=40, le=90)
    event_queue_capacity: int = Field(default=256, ge=32, le=4096)
    live_event_queue_capacity: int = Field(default=64, ge=8, le=512)
    max_live_event_subscribers: int = Field(default=16, ge=1, le=128)
    session_cookie_name: str = "garage_lpr_session"
    csrf_cookie_name: str = "garage_lpr_csrf"
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    secure_cookies: bool = False
    login_max_attempts: int = Field(default=5, ge=3, le=20)
    login_lock_seconds: int = Field(default=60, ge=10, le=3600)

    @field_validator(
        "log_directory",
        "snapshot_directory",
        "frontend_dist_directory",
        "secret_key_path",
        mode="after",
    )
    @classmethod
    def resolve_repository_path(cls, value: Path, info: ValidationInfo) -> Path:
        if value.is_absolute():
            return value
        if info.field_name == "frontend_dist_directory":
            return (repository_root() / value).resolve()
        return (runtime_root() / value).resolve()

    @field_validator("database_url", mode="after")
    @classmethod
    def resolve_relative_sqlite_url(cls, value: str) -> str:
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        database_path = value.removeprefix(prefix)
        if database_path == ":memory:" or Path(database_path).is_absolute():
            return value
        absolute_path = (runtime_root() / database_path).resolve().as_posix()
        return f"{prefix}{absolute_path}"


class RuntimeSettings(BaseModel):
    """Validated settings editable from the local administration UI."""

    simulation_mode: bool = True
    maintenance_mode: bool = True
    metrics_poll_interval_seconds: int = Field(default=10, ge=5, le=300)
    snapshot_enabled: bool = False
    snapshot_retention_days: int = Field(default=30, ge=1, le=3650)
    event_retention_days: int = Field(default=90, ge=1, le=3650)
    detection_fps: float = Field(default=5.0, ge=0.5, le=15.0)
    inference_provider: Literal["auto", "cpu", "cuda"] = "auto"
    detector_model_path: str = Field(
        default="models/license_plate_detector.onnx", min_length=1, max_length=1024
    )
    detector_output_format: Literal["xyxy", "yolo_v8"] = "xyxy"
    detector_input_width: int = Field(default=640, ge=160, le=1280, multiple_of=32)
    detector_input_height: int = Field(default=640, ge=160, le=1280, multiple_of=32)
    detector_confidence_threshold: float = Field(default=0.70, ge=0.1, le=1.0)
    detector_iou_threshold: float = Field(default=0.45, ge=0.1, le=0.9)
    max_plates_per_frame: int = Field(default=3, ge=1, le=10)
    ocr_model_path: str = Field(
        default="models/license_plate_ocr.onnx", min_length=1, max_length=1024
    )
    ocr_input_width: int = Field(default=160, ge=64, le=512)
    ocr_input_height: int = Field(default=48, ge=16, le=128)
    ocr_input_channels: Literal[1, 3] = 1
    ocr_charset: str = Field(
        default="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_length=10, max_length=128
    )
    recognition_min_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    required_confirmations: int = Field(default=3, ge=2, le=10)
    confirmation_window_ms: int = Field(default=2000, ge=250, le=10000)
    tracking_iou_threshold: float = Field(default=0.30, ge=0.05, le=0.95)
    tracking_max_idle_ms: int = Field(default=1500, ge=250, le=10000)
    max_active_tracks: int = Field(default=128, ge=10, le=2048)
    local_timezone: str = Field(default="Europe/Istanbul", min_length=1, max_length=128)
    gate_cooldown_seconds: int = Field(default=20, ge=1, le=3600)
    global_gate_cooldown_seconds: int = Field(default=3, ge=1, le=3600)
    gate_command_timeout_seconds: float = Field(default=2.0, ge=0.1, le=30.0)
    plate_detection_event_interval_seconds: float = Field(default=5.0, ge=1.0, le=300.0)

    @field_validator("detector_model_path", "ocr_model_path")
    @classmethod
    def normalize_model_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Model path must not be blank")
        return normalized

    @field_validator("ocr_charset")
    @classmethod
    def validate_ocr_charset(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(set(normalized)) != len(normalized):
            raise ValueError("OCR charset must not contain duplicate characters")
        if not normalized.isascii() or not normalized.isalnum():
            raise ValueError("OCR charset must contain only ASCII letters and digits")
        return normalized

    @field_validator("local_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        normalized = value.strip()
        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Timezone must be a valid IANA timezone") from error
        return normalized
