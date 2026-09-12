from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from garage_lpr.access.authorization import AuthorizationService
from garage_lpr.access.status import AuthorizationStatus
from garage_lpr.database.models import Vehicle


class Vehicles:
    def __init__(self, vehicle: Vehicle | None) -> None:
        self.vehicle = vehicle

    def get_by_plate(self, plate: str) -> Vehicle | None:
        return self.vehicle if self.vehicle and self.vehicle.plate == plate else None


def _vehicle(**overrides: object) -> Vehicle:
    values: dict[str, object] = {
        "id": 1,
        "plate": "34ABC123",
        "owner": "Ada Lovelace",
        "active": True,
        "allowed_days": list(range(7)),
    }
    values.update(overrides)
    return Vehicle(**values)


def _authorize(vehicle: Vehicle | None, observed_at: datetime) -> AuthorizationStatus:
    service = AuthorizationService(Vehicles(vehicle), ZoneInfo("Europe/Istanbul"))
    return service.authorize("34ABC123", 1, observed_at).status


def test_authorization_returns_required_statuses() -> None:
    observed = datetime(2026, 9, 11, 9, tzinfo=UTC)

    assert _authorize(None, observed) is AuthorizationStatus.UNAUTHORIZED
    assert _authorize(_vehicle(active=False), observed) is AuthorizationStatus.DISABLED
    assert (
        _authorize(_vehicle(valid_until=date(2026, 9, 10)), observed) is AuthorizationStatus.EXPIRED
    )
    assert (
        _authorize(_vehicle(allowed_days=[]), observed) is AuthorizationStatus.OUTSIDE_ALLOWED_TIME
    )
    assert _authorize(_vehicle(), observed) is AuthorizationStatus.AUTHORIZED


def test_authorization_handles_cross_midnight_schedule_by_start_day() -> None:
    friday_late = datetime(2026, 9, 11, 22, 30, tzinfo=ZoneInfo("Europe/Istanbul"))
    saturday_early = datetime(2026, 9, 12, 1, 30, tzinfo=ZoneInfo("Europe/Istanbul"))
    vehicle = _vehicle(
        allowed_days=[4],
        allowed_start_time=time(22),
        allowed_end_time=time(2),
    )

    assert _authorize(vehicle, friday_late) is AuthorizationStatus.AUTHORIZED
    assert _authorize(vehicle, saturday_early) is AuthorizationStatus.AUTHORIZED
