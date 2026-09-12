from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from garage_lpr.database.base import Base, TimestampMixin


class CameraType(StrEnum):
    RTSP = "RTSP"
    USB = "USB"
    ONVIF = "ONVIF"
    HTTP = "HTTP"


class GateControllerType(StrEnum):
    MOCK = "MOCK"
    HTTP = "HTTP"
    MQTT = "MQTT"
    SERIAL = "SERIAL"


class UserRole(StrEnum):
    ADMIN = "ADMIN"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=UserRole.ADMIN, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Camera(TimestampMixin, Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    camera_type: Mapped[str] = mapped_column(String(20), default=CameraType.RTSP)
    stream_url: Mapped[str] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    credentials_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    capture_fps_limit: Mapped[float] = mapped_column(Float, default=25.0)
    detection_fps: Mapped[float] = mapped_column(Float, default=5.0)
    requested_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    roi: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    connection_timeout_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    reconnect_schedule_seconds: Mapped[list[int]] = mapped_column(
        JSON, default=lambda: [1, 2, 5, 10, 30]
    )


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    allowed_days: Mapped[list[int]] = mapped_column(JSON, default=lambda: list(range(7)))
    allowed_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    allowed_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class GateControllerConfig(TimestampMixin, Base):
    __tablename__ = "gate_controllers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    controller_type: Mapped[str] = mapped_column(String(20), default=GateControllerType.MOCK)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pulse_ms: Mapped[int] = mapped_column(Integer, default=500)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    credentials_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class AccessRule(TimestampMixin, Base):
    __tablename__ = "access_rules"
    __table_args__ = (UniqueConstraint("vehicle_id", "camera_id", "gate_controller_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    camera_id: Mapped[int | None] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"), nullable=True
    )
    gate_controller_id: Mapped[int] = mapped_column(
        ForeignKey("gate_controllers.id", ondelete="CASCADE")
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RecognitionEvent(Base):
    __tablename__ = "recognition_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    camera_id: Mapped[int | None] = mapped_column(
        ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True
    )
    plate: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class AccessEvent(Base):
    __tablename__ = "access_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    recognition_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("recognition_events.id", ondelete="SET NULL"), nullable=True
    )
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True
    )
    gate_controller_id: Mapped[int | None] = mapped_column(
        ForeignKey("gate_controllers.id", ondelete="SET NULL"), nullable=True
    )
    plate: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
