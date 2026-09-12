from typing import Any

from garage_lpr.camera.domain import CameraRuntimeConfiguration
from garage_lpr.camera.rtsp import RTSPCameraProvider


class Image:
    shape = (720, 1280, 3)


class Capture:
    def __init__(self) -> None:
        self.opened = True
        self.settings: list[tuple[int, float]] = []

    def isOpened(self) -> bool:  # noqa: N802
        return self.opened

    def read(self) -> tuple[bool, Any]:
        return True, Image()

    def get(self, property_id: int) -> float:
        return 25.0

    def set(self, property_id: int, value: float) -> bool:
        self.settings.append((property_id, value))
        return True

    def release(self) -> None:
        self.opened = False


class Factory:
    fps_property = 5
    width_property = 3
    height_property = 4

    def __init__(self) -> None:
        self.source = ""
        self.timeout_ms = 0
        self.capture = Capture()

    def open(self, source: str, timeout_ms: int) -> Capture:
        self.source = source
        self.timeout_ms = timeout_ms
        return self.capture


def test_rtsp_provider_injects_encoded_credentials_and_reads_metadata() -> None:
    factory = Factory()
    configuration = CameraRuntimeConfiguration(
        camera_id=1,
        stream_url="rtsp://camera.local:554/live?profile=main",
        username="garage user",
        password="p@ss word",
        requested_width=1280,
        requested_height=720,
        connection_timeout_seconds=3,
    )
    provider = RTSPCameraProvider(configuration, factory)

    provider.connect()
    frame = provider.read()

    assert factory.source == (
        "rtsp://garage%20user:p%40ss%20word@camera.local:554/live?profile=main"
    )
    assert factory.timeout_ms == 3000
    assert factory.capture.settings == [(3, 1280.0), (4, 720.0)]
    assert frame is not None
    assert (frame.width, frame.height, frame.sequence) == (1280, 720, 1)
    assert provider.reported_fps == 25.0

    provider.close()
    assert provider.healthy() is False
