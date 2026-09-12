from threading import Lock

from garage_lpr.camera.contracts import CameraFrame


class LatestFrameBuffer:
    """A capacity-one buffer: producers never wait and stale frames never accumulate."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._frame: CameraFrame | None = None
        self._last_read_sequence: int | None = None
        self._replaced_frames = 0

    def put(self, frame: CameraFrame) -> None:
        with self._lock:
            if self._frame is not None and self._frame.sequence != self._last_read_sequence:
                self._replaced_frames += 1
            self._frame = frame

    def latest(self, after_sequence: int | None = None) -> CameraFrame | None:
        with self._lock:
            if self._frame is None or self._frame.sequence == after_sequence:
                return None
            self._last_read_sequence = self._frame.sequence
            return self._frame

    def clear(self) -> None:
        """Drop a stale frame before a camera worker is restarted."""
        with self._lock:
            self._frame = None
            self._last_read_sequence = None
            self._replaced_frames = 0

    @property
    def replaced_frames(self) -> int:
        with self._lock:
            return self._replaced_frames
