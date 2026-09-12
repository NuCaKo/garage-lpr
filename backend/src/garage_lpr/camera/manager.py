import logging
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import monotonic_ns

from garage_lpr.camera.buffer import LatestFrameBuffer
from garage_lpr.camera.contracts import CameraFrame, CameraProvider
from garage_lpr.camera.domain import (
    CameraRuntimeConfiguration,
    CameraRuntimeSnapshot,
    CameraRuntimeState,
)
from garage_lpr.camera.stream import CameraStreamLoop

ProviderFactory = Callable[[CameraRuntimeConfiguration], CameraProvider]
StateObserver = Callable[
    [int, CameraRuntimeState | None, CameraRuntimeState, str],
    None,
]


class CameraWorkerStopError(RuntimeError):
    pass


@dataclass(slots=True)
class _Worker:
    configuration: CameraRuntimeConfiguration
    stop_event: Event
    thread: Thread


class CameraManager:
    """Owns a bounded set of long-lived camera workers and capacity-one buffers."""

    def __init__(
        self,
        provider_factory: ProviderFactory,
        max_active_cameras: int = 1,
        state_observer: StateObserver | None = None,
    ) -> None:
        self._provider_factory = provider_factory
        self._max_active_cameras = max_active_cameras
        self._lock = Lock()
        self._workers: dict[int, _Worker] = {}
        self._buffers: dict[int, LatestFrameBuffer] = {}
        self._snapshots: dict[int, CameraRuntimeSnapshot] = {}
        self._active_ids: set[int] = set()
        self._state_observer = state_observer
        self._logger = logging.getLogger("garage_lpr.camera.manager")

    def apply(self, configuration: CameraRuntimeConfiguration) -> None:
        self.stop(configuration.camera_id)
        with self._lock:
            if len(self._workers) >= self._max_active_cameras:
                raise ValueError("Active camera limit reached")
            buffer = self._buffers.setdefault(configuration.camera_id, LatestFrameBuffer())
            buffer.clear()
            stop_event = Event()
            loop = CameraStreamLoop(
                configuration=configuration,
                provider_builder=lambda: self._provider_factory(configuration),
                on_frame=lambda frame: self._receive_frame(configuration.camera_id, buffer, frame),
                on_state=lambda state, detail: self._set_state(
                    configuration.camera_id, buffer, state, detail
                ),
            )
            thread = Thread(
                target=loop.run,
                args=(stop_event,),
                name=f"camera-{configuration.camera_id}",
                daemon=True,
            )
            self._workers[configuration.camera_id] = _Worker(
                configuration=configuration,
                stop_event=stop_event,
                thread=thread,
            )
            self._active_ids.add(configuration.camera_id)
            self._snapshots[configuration.camera_id] = self._new_snapshot(
                configuration.camera_id,
                CameraRuntimeState.STOPPED,
                "Camera worker starting",
                buffer,
            )
        try:
            thread.start()
        except Exception:
            with self._lock:
                self._workers.pop(configuration.camera_id, None)
                self._active_ids.discard(configuration.camera_id)
            raise

    def stop(self, camera_id: int) -> None:
        with self._lock:
            worker = self._workers.get(camera_id)
        if worker is None:
            return
        worker.stop_event.set()
        join_timeout = worker.configuration.connection_timeout_seconds + 1.0
        worker.thread.join(timeout=join_timeout)
        if worker.thread.is_alive():
            with self._lock:
                buffer = self._buffers.get(camera_id, LatestFrameBuffer())
                self._snapshots[camera_id] = self._new_snapshot(
                    camera_id,
                    CameraRuntimeState.UNAVAILABLE,
                    "Camera worker did not stop within its timeout",
                    buffer,
                )
            raise CameraWorkerStopError("Camera worker did not stop within its timeout")
        with self._lock:
            self._workers.pop(camera_id, None)
            self._active_ids.discard(camera_id)
            buffer = self._buffers.get(camera_id, LatestFrameBuffer())
            previous = self._snapshots.get(camera_id)
            self._snapshots[camera_id] = CameraRuntimeSnapshot(
                camera_id=camera_id,
                state=CameraRuntimeState.STOPPED,
                detail="Camera worker stopped",
                frames_received=previous.frames_received if previous else 0,
                frames_replaced=buffer.replaced_frames,
                last_frame_monotonic_ns=(previous.last_frame_monotonic_ns if previous else None),
            )
        self._notify_state(
            camera_id,
            previous.state if previous else None,
            CameraRuntimeState.STOPPED,
            "Camera worker stopped",
        )

    def shutdown(self) -> None:
        with self._lock:
            camera_ids = tuple(self._workers)
        for camera_id in camera_ids:
            self.stop(camera_id)

    def latest_frame(self, camera_id: int, after_sequence: int | None = None) -> CameraFrame | None:
        with self._lock:
            buffer = self._buffers.get(camera_id)
        return buffer.latest(after_sequence) if buffer is not None else None

    def snapshot(self, camera_id: int) -> CameraRuntimeSnapshot:
        with self._lock:
            return self._snapshots.get(
                camera_id,
                CameraRuntimeSnapshot(
                    camera_id=camera_id,
                    state=CameraRuntimeState.STOPPED,
                    detail="Camera is inactive",
                    frames_received=0,
                    frames_replaced=0,
                    last_frame_monotonic_ns=None,
                ),
            )

    def snapshots(self) -> tuple[CameraRuntimeSnapshot, ...]:
        with self._lock:
            return tuple(
                snapshot
                for camera_id, snapshot in self._snapshots.items()
                if camera_id in self._active_ids
            )

    def mark_unavailable(self, camera_id: int, detail: str) -> None:
        with self._lock:
            buffer = self._buffers.setdefault(camera_id, LatestFrameBuffer())
            self._active_ids.add(camera_id)
            previous = self._snapshots.get(camera_id)
            self._snapshots[camera_id] = self._new_snapshot(
                camera_id, CameraRuntimeState.UNAVAILABLE, detail, buffer
            )
        self._notify_state(
            camera_id,
            previous.state if previous else None,
            CameraRuntimeState.UNAVAILABLE,
            detail,
        )

    def _receive_frame(self, camera_id: int, buffer: LatestFrameBuffer, frame: CameraFrame) -> None:
        with self._lock:
            previous = self._snapshots.get(camera_id)
            sequence = (previous.frames_received if previous else 0) + 1
        managed_frame = CameraFrame(
            image=frame.image,
            captured_monotonic_ns=frame.captured_monotonic_ns,
            sequence=sequence,
            width=frame.width,
            height=frame.height,
        )
        buffer.put(managed_frame)
        with self._lock:
            self._snapshots[camera_id] = CameraRuntimeSnapshot(
                camera_id=camera_id,
                state=CameraRuntimeState.CONNECTED,
                detail="Receiving frames",
                frames_received=sequence,
                frames_replaced=buffer.replaced_frames,
                last_frame_monotonic_ns=monotonic_ns(),
            )
        if previous is None or previous.state is not CameraRuntimeState.CONNECTED:
            self._notify_state(
                camera_id,
                previous.state if previous else None,
                CameraRuntimeState.CONNECTED,
                "Receiving frames",
            )

    def _set_state(
        self,
        camera_id: int,
        buffer: LatestFrameBuffer,
        state: CameraRuntimeState,
        detail: str,
    ) -> None:
        with self._lock:
            previous = self._snapshots.get(camera_id)
            self._snapshots[camera_id] = CameraRuntimeSnapshot(
                camera_id=camera_id,
                state=state,
                detail=detail,
                frames_received=previous.frames_received if previous else 0,
                frames_replaced=buffer.replaced_frames,
                last_frame_monotonic_ns=(previous.last_frame_monotonic_ns if previous else None),
            )
        if previous is None or previous.state is not state:
            self._notify_state(camera_id, previous.state if previous else None, state, detail)

    def _notify_state(
        self,
        camera_id: int,
        previous: CameraRuntimeState | None,
        current: CameraRuntimeState,
        detail: str,
    ) -> None:
        if self._state_observer is None:
            return
        try:
            self._state_observer(camera_id, previous, current, detail)
        except Exception as error:
            self._logger.error(
                "camera_state_observer_failed",
                extra={
                    "metadata": {
                        "camera_id": camera_id,
                        "error_type": type(error).__name__,
                    }
                },
            )

    @staticmethod
    def _new_snapshot(
        camera_id: int,
        state: CameraRuntimeState,
        detail: str,
        buffer: LatestFrameBuffer,
    ) -> CameraRuntimeSnapshot:
        return CameraRuntimeSnapshot(
            camera_id=camera_id,
            state=state,
            detail=detail,
            frames_received=0,
            frames_replaced=buffer.replaced_frames,
            last_frame_monotonic_ns=None,
        )
