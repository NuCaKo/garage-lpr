import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from garage_lpr.access.status import AuthorizationStatus
from garage_lpr.database.models import Vehicle
from garage_lpr.database.repositories.vehicles import VehicleRepository


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    status: AuthorizationStatus
    vehicle_id: int | None
    reason: str


class AuthorizationResolver(Protocol):
    def authorize(
        self,
        plate: str,
        camera_id: int,
        observed_at: datetime,
    ) -> AuthorizationDecision: ...


class VehicleLookup(Protocol):
    def get_by_plate(self, plate: str) -> Vehicle | None: ...


class AuthorizationService:
    """Evaluates one vehicle against its persisted validity and schedule."""

    def __init__(self, repository: VehicleLookup, timezone: ZoneInfo) -> None:
        self._repository = repository
        self._timezone = timezone

    def authorize(
        self,
        plate: str,
        camera_id: int,
        observed_at: datetime,
    ) -> AuthorizationDecision:
        del camera_id  # Camera-to-gate access-rule binding begins with the gate phase.
        vehicle = self._repository.get_by_plate(plate)
        if vehicle is None:
            return AuthorizationDecision(
                AuthorizationStatus.UNAUTHORIZED, None, "VEHICLE_NOT_FOUND"
            )
        if not vehicle.active:
            return AuthorizationDecision(
                AuthorizationStatus.DISABLED, vehicle.id, "VEHICLE_DISABLED"
            )
        local = _as_aware(observed_at).astimezone(self._timezone)
        if vehicle.valid_from is not None and local.date() < vehicle.valid_from:
            return AuthorizationDecision(
                AuthorizationStatus.EXPIRED, vehicle.id, "VALIDITY_NOT_STARTED"
            )
        if vehicle.valid_until is not None and local.date() > vehicle.valid_until:
            return AuthorizationDecision(
                AuthorizationStatus.EXPIRED, vehicle.id, "VALIDITY_EXPIRED"
            )
        if not _inside_schedule(vehicle, local):
            return AuthorizationDecision(
                AuthorizationStatus.OUTSIDE_ALLOWED_TIME,
                vehicle.id,
                "OUTSIDE_ALLOWED_SCHEDULE",
            )
        return AuthorizationDecision(AuthorizationStatus.AUTHORIZED, vehicle.id, "AUTHORIZED")


class DatabaseAuthorizationResolver:
    """Creates a short SQLAlchemy session only after temporal confirmation."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        timezone_name: str,
    ) -> None:
        self._session_factory = session_factory
        self._timezone = ZoneInfo(timezone_name)
        self._logger = logging.getLogger("garage_lpr.authorization")

    def authorize(
        self,
        plate: str,
        camera_id: int,
        observed_at: datetime,
    ) -> AuthorizationDecision:
        session: Session | None = None
        try:
            session = self._session_factory()
            return AuthorizationService(VehicleRepository(session), self._timezone).authorize(
                plate, camera_id, observed_at
            )
        except SQLAlchemyError as error:
            if session is not None:
                session.rollback()
            self._logger.error(
                "authorization_database_unavailable",
                extra={"metadata": {"error_type": type(error).__name__}},
            )
            return AuthorizationDecision(
                AuthorizationStatus.UNAUTHORIZED, None, "AUTHORIZATION_UNAVAILABLE"
            )
        finally:
            if session is not None:
                session.close()


def _as_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _inside_schedule(vehicle: Vehicle, observed_at: datetime) -> bool:
    allowed_days = set(vehicle.allowed_days or [])
    start = vehicle.allowed_start_time
    end = vehicle.allowed_end_time
    current = observed_at.time().replace(tzinfo=None)
    schedule_day = observed_at.weekday()
    if start is None or end is None:
        return schedule_day in allowed_days
    if start <= end:
        return schedule_day in allowed_days and start <= current <= end
    if current >= start:
        return schedule_day in allowed_days
    if current <= end:
        return (schedule_day - 1) % 7 in allowed_days
    return False
