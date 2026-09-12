from threading import Lock

from garage_lpr.camera.contracts import CameraFrame


class JpegPreviewEncoder:
    def __init__(self, quality: int) -> None:
        import cv2

        self._cv2 = cv2
        self._quality = quality
        self._lock = Lock()
        self._cache: dict[int, tuple[tuple[int, int], bytes]] = {}

    def encode(self, camera_id: int, frame: CameraFrame) -> bytes:
        with self._lock:
            cached = self._cache.get(camera_id)
            frame_key = (frame.sequence, frame.captured_monotonic_ns)
            if cached is not None and cached[0] == frame_key:
                return cached[1]
            success, encoded = self._cv2.imencode(
                ".jpg",
                frame.image,
                [self._cv2.IMWRITE_JPEG_QUALITY, self._quality],
            )
            if not success:
                raise ValueError("Preview frame could not be encoded")
            payload = encoded.tobytes()
            self._cache[camera_id] = (frame_key, payload)
            return payload

    def evict(self, camera_id: int) -> None:
        with self._lock:
            self._cache.pop(camera_id, None)
