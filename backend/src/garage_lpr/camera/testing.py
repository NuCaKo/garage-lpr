from collections.abc import Callable
from time import perf_counter

from garage_lpr.camera.domain import CameraConnectionResult, CameraRuntimeConfiguration
from garage_lpr.camera.rtsp import RTSPCameraProvider

ProviderFactory = Callable[[CameraRuntimeConfiguration], RTSPCameraProvider]


class CameraConnectionTester:
    def __init__(self, provider_factory: ProviderFactory) -> None:
        self._provider_factory = provider_factory

    def test(self, configuration: CameraRuntimeConfiguration) -> CameraConnectionResult:
        provider = self._provider_factory(configuration)
        started = perf_counter()
        try:
            provider.connect()
            frame = provider.read()
            if frame is None:
                return CameraConnectionResult(
                    connected=False,
                    latency_ms=_elapsed_ms(started),
                    width=None,
                    height=None,
                    fps=None,
                    detail="Connected, but no frame was received",
                )
            return CameraConnectionResult(
                connected=True,
                latency_ms=_elapsed_ms(started),
                width=frame.width,
                height=frame.height,
                fps=provider.reported_fps,
                detail="Frame received",
            )
        except Exception:
            return CameraConnectionResult(
                connected=False,
                latency_ms=_elapsed_ms(started),
                width=None,
                height=None,
                fps=None,
                detail="Connection failed or timed out",
            )
        finally:
            provider.close()


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)
