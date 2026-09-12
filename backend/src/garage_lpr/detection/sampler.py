from time import monotonic_ns

from garage_lpr.camera.contracts import CameraFrame


class FrameSampler:
    """Accepts at most one latest frame per configured detection interval."""

    def __init__(self, detection_fps: float) -> None:
        if detection_fps <= 0:
            raise ValueError("Detection FPS must be positive")
        self._interval_ns = round(1_000_000_000 / detection_fps)
        self._last_sample_ns: int | None = None

    @property
    def interval_seconds(self) -> float:
        return self._interval_ns / 1_000_000_000

    def should_process(self, frame: CameraFrame) -> bool:
        timestamp = frame.captured_monotonic_ns
        if (
            self._last_sample_ns is not None
            and timestamp >= self._last_sample_ns
            and timestamp - self._last_sample_ns < self._interval_ns
        ):
            return False
        self._last_sample_ns = timestamp
        return True

    def seconds_until_due(self) -> float:
        if self._last_sample_ns is None:
            return 0.0
        remaining = self._interval_ns - (monotonic_ns() - self._last_sample_ns)
        return max(0.0, remaining / 1_000_000_000)
