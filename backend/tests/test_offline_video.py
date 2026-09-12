from pathlib import Path
from typing import Any

import numpy as np

from garage_lpr.detection.pipeline import DetectionPipelineResult
from garage_lpr.offline_video import OfflineVideoRunner


class Capture:
    def __init__(self) -> None:
        self.index = 0
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802
        return True

    def read(self) -> tuple[bool, Any]:
        if self.index >= 10:
            return False, None
        self.index += 1
        return True, np.zeros((72, 128, 3), dtype=np.uint8)

    def get(self, property_id: int) -> float:
        return 25.0

    def release(self) -> None:
        self.released = True


class CV2:
    CAP_PROP_FPS = 5

    def __init__(self) -> None:
        self.capture = Capture()

    def VideoCapture(self, source: str) -> Capture:  # noqa: N802
        return self.capture


class Pipeline:
    def __init__(self) -> None:
        self.sequences: list[int] = []

    def process(self, camera_id: int, frame: Any, roi: Any) -> DetectionPipelineResult:
        self.sequences.append(frame.sequence)
        return DetectionPipelineResult(camera_id, frame.sequence, (), 0, 0, 1, 0, 1)


def test_offline_runner_samples_video_without_accumulating_frames() -> None:
    cv2 = CV2()
    pipeline = Pipeline()
    runner = OfflineVideoRunner(pipeline, detection_fps=5, cv2_module=cv2)  # type: ignore[arg-type]

    summary = runner.run(Path("recording.mp4"))

    assert summary.frames_read == 10
    assert summary.frames_sampled == 2
    assert pipeline.sequences == [1, 6]
    assert cv2.capture.released is True
