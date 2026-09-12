from threading import Event
from typing import Any

from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.domain import NormalizedROI
from garage_lpr.config.settings import RuntimeSettings
from garage_lpr.detection.pipeline import DetectionPipelineResult
from garage_lpr.inference.domain import InferenceCameraConfiguration
from garage_lpr.inference.factory import PipelineBundle
from garage_lpr.inference.manager import InferenceManager


class CameraFrames:
    def __init__(self) -> None:
        self.frame = CameraFrame(object(), 1_000_000_000, 1, 1280, 720)

    def latest_frame(self, camera_id: int, after_sequence: int | None = None) -> CameraFrame | None:
        return None if after_sequence == self.frame.sequence else self.frame


class Pipeline:
    def __init__(self) -> None:
        self.called = Event()

    def process(self, camera_id: int, frame: Any, roi: Any) -> DetectionPipelineResult:
        self.called.set()
        return DetectionPipelineResult(camera_id, frame.sequence, (), 0, 0, 1, 0, 1)


def test_inference_manager_uses_one_worker_and_scalar_metrics() -> None:
    pipeline = Pipeline()
    manager = InferenceManager(
        CameraFrames(),  # type: ignore[arg-type]
        lambda settings: PipelineBundle(
            pipeline,  # type: ignore[arg-type]
            "CPUExecutionProvider",
            "CPUExecutionProvider",
        ),
    )
    manager.configure(RuntimeSettings())
    manager.apply_camera(InferenceCameraConfiguration(1, True, 5, NormalizedROI()))

    assert pipeline.called.wait(1.0)
    snapshot = manager.snapshot()
    manager.shutdown()

    assert snapshot.frames_sampled == 1
    assert snapshot.frame_buffer_capacity == 1
    assert snapshot.queue_size == 0
