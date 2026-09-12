class ReconnectBackoff:
    def __init__(self, schedule_seconds: tuple[float, ...]) -> None:
        if not schedule_seconds or any(delay <= 0 for delay in schedule_seconds):
            raise ValueError("Reconnect schedule must contain positive delays")
        self._schedule = schedule_seconds
        self._attempt = 0

    def next_delay(self) -> float:
        index = min(self._attempt, len(self._schedule) - 1)
        self._attempt += 1
        return self._schedule[index]

    def reset(self) -> None:
        self._attempt = 0
