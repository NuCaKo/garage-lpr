from dataclasses import dataclass
from enum import StrEnum
from threading import Lock


class CooldownStatus(StrEnum):
    ALLOWED = "ALLOWED"
    PLATE_COOLDOWN = "PLATE_COOLDOWN"
    GLOBAL_COOLDOWN = "GLOBAL_COOLDOWN"


@dataclass(frozen=True, slots=True)
class CooldownDecision:
    status: CooldownStatus
    retry_after_seconds: float


class CooldownManager:
    """Atomically reserves bounded plate/global trigger windows."""

    def __init__(
        self,
        plate_cooldown_seconds: float,
        global_cooldown_seconds: float,
        max_plate_entries: int = 1024,
    ) -> None:
        if plate_cooldown_seconds < 0 or global_cooldown_seconds < 0:
            raise ValueError("Cooldown values cannot be negative")
        if max_plate_entries < 1:
            raise ValueError("Cooldown cache capacity must be positive")
        self._plate_window_ns = round(plate_cooldown_seconds * 1_000_000_000)
        self._global_window_ns = round(global_cooldown_seconds * 1_000_000_000)
        self._max_plate_entries = max_plate_entries
        self._plate_triggers: dict[str, int] = {}
        self._last_global_trigger_ns: int | None = None
        self._lock = Lock()

    def check_and_reserve(self, plate: str, observed_ns: int) -> CooldownDecision:
        with self._lock:
            self._prune(observed_ns)
            last_plate = self._plate_triggers.get(plate)
            if last_plate is not None:
                remaining = self._plate_window_ns - (observed_ns - last_plate)
                if remaining > 0:
                    return CooldownDecision(
                        CooldownStatus.PLATE_COOLDOWN,
                        round(remaining / 1_000_000_000, 3),
                    )
            if self._last_global_trigger_ns is not None:
                remaining = self._global_window_ns - (observed_ns - self._last_global_trigger_ns)
                if remaining > 0:
                    return CooldownDecision(
                        CooldownStatus.GLOBAL_COOLDOWN,
                        round(remaining / 1_000_000_000, 3),
                    )
            if len(self._plate_triggers) >= self._max_plate_entries:
                oldest = min(self._plate_triggers, key=self._plate_triggers.__getitem__)
                self._plate_triggers.pop(oldest, None)
            self._plate_triggers[plate] = observed_ns
            self._last_global_trigger_ns = observed_ns
            return CooldownDecision(CooldownStatus.ALLOWED, 0.0)

    def _prune(self, observed_ns: int) -> None:
        expired = [
            plate
            for plate, triggered_ns in self._plate_triggers.items()
            if observed_ns - triggered_ns >= self._plate_window_ns
        ]
        for plate in expired:
            self._plate_triggers.pop(plate, None)
