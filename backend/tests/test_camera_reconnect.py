from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.domain import CameraRuntimeConfiguration, CameraRuntimeState
from garage_lpr.camera.stream import CameraStreamLoop


class ControlledStopSignal:
    def __init__(self) -> None:
        self.stopped = False
        self.reconnect_waits: list[float] = []

    def is_set(self) -> bool:
        return self.stopped

    def wait(self, timeout: float) -> bool:
        if timeout >= 0.9:
            self.reconnect_waits.append(timeout)
            if len(self.reconnect_waits) == 2:
                self.stopped = True
        return self.stopped


class FakeProvider:
    def __init__(self, *, fail_connect: bool = False) -> None:
        self.fail_connect = fail_connect
        self.closed = False
        self.read_count = 0

    def connect(self) -> None:
        if self.fail_connect:
            raise ConnectionError("offline")

    def read(self) -> CameraFrame | None:
        self.read_count += 1
        if self.read_count > 1:
            return None
        return CameraFrame(object(), 1, 1, 1280, 720)

    def close(self) -> None:
        self.closed = True

    def healthy(self) -> bool:
        return not self.closed


def test_stream_reconnects_with_backoff_and_recovers() -> None:
    providers = [FakeProvider(fail_connect=True), FakeProvider()]
    frames: list[CameraFrame] = []
    states: list[CameraRuntimeState] = []
    stop = ControlledStopSignal()
    configuration = CameraRuntimeConfiguration(
        camera_id=7,
        stream_url="rtsp://camera.local/live",
        username=None,
        password=None,
        capture_fps_limit=25,
        reconnect_schedule_seconds=(1, 2, 5),
    )

    loop = CameraStreamLoop(
        configuration,
        provider_builder=lambda: providers.pop(0),
        on_frame=frames.append,
        on_state=lambda state, detail: states.append(state),
    )
    loop.run(stop)  # type: ignore[arg-type]

    assert stop.reconnect_waits == [1, 1]
    assert len(frames) == 1
    assert CameraRuntimeState.CONNECTED in states
    assert states[-1] is CameraRuntimeState.STOPPED
