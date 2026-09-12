import logging
from collections.abc import Callable
from time import monotonic
from typing import Protocol

from garage_lpr.camera.backoff import ReconnectBackoff
from garage_lpr.camera.contracts import CameraFrame, CameraProvider
from garage_lpr.camera.domain import CameraRuntimeConfiguration, CameraRuntimeState

ProviderBuilder = Callable[[], CameraProvider]
FrameHandler = Callable[[CameraFrame], None]
StateHandler = Callable[[CameraRuntimeState, str], None]


class StopSignal(Protocol):
    def is_set(self) -> bool: ...

    def wait(self, timeout: float) -> bool: ...


class CameraStreamLoop:
    """Runs one camera in one bounded lifecycle loop; it never creates threads itself."""

    def __init__(
        self,
        configuration: CameraRuntimeConfiguration,
        provider_builder: ProviderBuilder,
        on_frame: FrameHandler,
        on_state: StateHandler,
    ) -> None:
        self._configuration = configuration
        self._provider_builder = provider_builder
        self._on_frame = on_frame
        self._on_state = on_state
        self._logger = logging.getLogger(f"garage_lpr.camera.{configuration.camera_id}")

    def run(self, stop_event: StopSignal) -> None:
        backoff = ReconnectBackoff(self._configuration.reconnect_schedule_seconds)
        first_attempt = True
        while not stop_event.is_set():
            state = (
                CameraRuntimeState.CONNECTING if first_attempt else CameraRuntimeState.RECONNECTING
            )
            self._on_state(state, "Connecting to camera")
            provider: CameraProvider | None = None
            received_frame = False
            try:
                provider = self._provider_builder()
                provider.connect()
                received_frame = self._capture(provider, stop_event, backoff)
            except Exception as error:
                self._logger.warning(
                    "camera_connection_failed",
                    extra={
                        "metadata": {
                            "camera_id": self._configuration.camera_id,
                            "error_type": type(error).__name__,
                        }
                    },
                )
            finally:
                if provider is not None:
                    try:
                        provider.close()
                    except Exception as error:
                        self._logger.warning(
                            "camera_close_failed",
                            extra={
                                "metadata": {
                                    "camera_id": self._configuration.camera_id,
                                    "error_type": type(error).__name__,
                                }
                            },
                        )

            if stop_event.is_set():
                break
            if received_frame:
                backoff.reset()
            delay = backoff.next_delay()
            self._on_state(CameraRuntimeState.RECONNECTING, f"Retrying in {delay:g} seconds")
            stop_event.wait(delay)
            first_attempt = False
        self._on_state(CameraRuntimeState.STOPPED, "Camera worker stopped")

    def _capture(
        self,
        provider: CameraProvider,
        stop_event: StopSignal,
        backoff: ReconnectBackoff,
    ) -> bool:
        period_seconds = 1.0 / self._configuration.capture_fps_limit
        connected = False
        while not stop_event.is_set():
            started = monotonic()
            frame = provider.read()
            if frame is None:
                return connected
            if not connected:
                connected = True
                backoff.reset()
                self._on_state(CameraRuntimeState.CONNECTED, "Receiving frames")
            self._on_frame(frame)
            remaining = period_seconds - (monotonic() - started)
            if remaining > 0:
                stop_event.wait(remaining)
        return connected
