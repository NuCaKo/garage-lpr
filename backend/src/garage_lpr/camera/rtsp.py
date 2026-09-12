from time import monotonic_ns
from typing import Any, Protocol
from urllib.parse import quote, urlsplit, urlunsplit

from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.domain import CameraRuntimeConfiguration


class CameraConnectionError(RuntimeError):
    pass


class CaptureDevice(Protocol):
    def isOpened(self) -> bool: ...  # noqa: N802

    def read(self) -> tuple[bool, Any]: ...

    def get(self, property_id: int) -> float: ...

    def set(self, property_id: int, value: float) -> bool: ...

    def release(self) -> None: ...


class CaptureFactory(Protocol):
    def open(self, source: str, timeout_ms: int) -> CaptureDevice: ...

    @property
    def fps_property(self) -> int: ...

    @property
    def width_property(self) -> int: ...

    @property
    def height_property(self) -> int: ...


class OpenCVCaptureFactory:
    def __init__(self) -> None:
        import cv2

        cv2.setNumThreads(1)
        self._cv2 = cv2

    @property
    def fps_property(self) -> int:
        return int(self._cv2.CAP_PROP_FPS)

    @property
    def width_property(self) -> int:
        return int(self._cv2.CAP_PROP_FRAME_WIDTH)

    @property
    def height_property(self) -> int:
        return int(self._cv2.CAP_PROP_FRAME_HEIGHT)

    def open(self, source: str, timeout_ms: int) -> CaptureDevice:
        capture = self._cv2.VideoCapture()
        parameters = [
            self._cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            timeout_ms,
            self._cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            timeout_ms,
        ]
        opened = capture.open(source, self._cv2.CAP_FFMPEG, parameters)
        if not opened:
            capture.release()
            raise CameraConnectionError("RTSP stream could not be opened")
        capture.set(self._cv2.CAP_PROP_BUFFERSIZE, 1)
        return capture


class RTSPCameraProvider:
    def __init__(
        self,
        configuration: CameraRuntimeConfiguration,
        capture_factory: CaptureFactory,
    ) -> None:
        self._configuration = configuration
        self._capture_factory = capture_factory
        self._capture: CaptureDevice | None = None
        self._sequence = 0

    def connect(self) -> None:
        self.close()
        timeout_ms = max(1, int(self._configuration.connection_timeout_seconds * 1000))
        source = _source_with_credentials(
            self._configuration.stream_url,
            self._configuration.username,
            self._configuration.password,
        )
        self._capture = self._capture_factory.open(source, timeout_ms)
        if (
            self._configuration.requested_width is not None
            and self._configuration.requested_height is not None
        ):
            self._capture.set(
                self._capture_factory.width_property,
                float(self._configuration.requested_width),
            )
            self._capture.set(
                self._capture_factory.height_property,
                float(self._configuration.requested_height),
            )

    def read(self) -> CameraFrame | None:
        if self._capture is None or not self._capture.isOpened():
            return None
        success, image = self._capture.read()
        if not success or image is None or not hasattr(image, "shape"):
            return None
        height, width = image.shape[:2]
        self._sequence += 1
        return CameraFrame(
            image=image,
            captured_monotonic_ns=monotonic_ns(),
            sequence=self._sequence,
            width=int(width),
            height=int(height),
        )

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def healthy(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    @property
    def reported_fps(self) -> float | None:
        if self._capture is None:
            return None
        fps = float(self._capture.get(self._capture_factory.fps_property))
        return fps if fps > 0 else None


def _source_with_credentials(url: str, username: str | None, password: str | None) -> str:
    if not username:
        return url
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    host = f"[{hostname}]" if ":" in hostname else hostname
    port = f":{parsed.port}" if parsed.port is not None else ""
    encoded_user = quote(username, safe="")
    encoded_password = f":{quote(password, safe='')}" if password is not None else ""
    netloc = f"{encoded_user}{encoded_password}@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
