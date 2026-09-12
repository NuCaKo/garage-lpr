from collections import OrderedDict
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic


@dataclass(slots=True)
class _AttemptState:
    failures: int
    locked_until: float


class LoginAttemptLimiter:
    """Process-local bounded brute-force limiter; no polling or cleanup thread."""

    def __init__(
        self,
        max_attempts: int,
        lock_seconds: int,
        *,
        max_keys: int = 1024,
    ) -> None:
        self._max_attempts = max_attempts
        self._lock_seconds = lock_seconds
        self._max_keys = max_keys
        self._states: OrderedDict[str, _AttemptState] = OrderedDict()
        self._lock = Lock()

    def retry_after(self, key: str) -> int:
        now = monotonic()
        with self._lock:
            state = self._states.get(key)
            if state is None:
                return 0
            self._states.move_to_end(key)
            if state.locked_until > now:
                return max(1, ceil(state.locked_until - now))
            if state.locked_until:
                self._states.pop(key, None)
            return 0

    def record_failure(self, key: str) -> int:
        now = monotonic()
        with self._lock:
            state = self._states.get(key)
            if state is None:
                if len(self._states) >= self._max_keys:
                    self._states.popitem(last=False)
                state = _AttemptState(failures=0, locked_until=0.0)
                self._states[key] = state
            state.failures += 1
            self._states.move_to_end(key)
            if state.failures >= self._max_attempts:
                state.failures = 0
                state.locked_until = now + self._lock_seconds
                return self._lock_seconds
            return 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._states.pop(key, None)
