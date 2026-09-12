from threading import Lock
from time import monotonic_ns

from garage_lpr.gate.contracts import GateCommandResult, GateState


class MockGateController:
    """Thread-safe pulse controller whose state expires without timers or polling."""

    def __init__(self, pulse_ms: int = 500, available: bool = True) -> None:
        if pulse_ms < 1:
            raise ValueError("Pulse duration must be positive")
        self._pulse_ns = pulse_ms * 1_000_000
        self._available = available
        self._open_until_ns = 0
        self._open_calls = 0
        self._lock = Lock()

    @property
    def open_calls(self) -> int:
        with self._lock:
            return self._open_calls

    def open(self) -> GateCommandResult:
        with self._lock:
            if not self._available:
                return GateCommandResult(False, "MOCK_GATE_UNAVAILABLE")
            self._open_calls += 1
            self._open_until_ns = monotonic_ns() + self._pulse_ns
            return GateCommandResult(True, "MOCK_GATE_PULSE_ACCEPTED")

    def close(self) -> GateCommandResult:
        with self._lock:
            if not self._available:
                return GateCommandResult(False, "MOCK_GATE_UNAVAILABLE")
            self._open_until_ns = 0
            return GateCommandResult(True, "MOCK_GATE_CLOSED")

    def status(self) -> GateState:
        with self._lock:
            if not self._available:
                return GateState.UNAVAILABLE
            return GateState.OPEN if monotonic_ns() < self._open_until_ns else GateState.CLOSED

    def health_check(self) -> bool:
        with self._lock:
            return self._available
