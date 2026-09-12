import argparse
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.domain import NormalizedROI
from garage_lpr.config.settings import RuntimeSettings
from garage_lpr.detection.pipeline import DetectionPipeline, DetectionPipelineResult
from garage_lpr.detection.sampler import FrameSampler
from garage_lpr.inference.factory import ProductionPipelineFactory
from garage_lpr.inference.runtime import ONNXRuntimeSessionFactory

ResultHandler = Callable[[DetectionPipelineResult], None]


class VideoCapture(Protocol):
    def isOpened(self) -> bool: ...  # noqa: N802

    def read(self) -> tuple[bool, Any]: ...

    def get(self, property_id: int) -> float: ...

    def release(self) -> None: ...


@dataclass(frozen=True, slots=True)
class OfflineRunSummary:
    frames_read: int
    frames_sampled: int
    detections: int
    ocr_calls: int
    valid_plates: int


class OfflineVideoRunner:
    """Feeds a recording through the same pipeline without retaining video frames."""

    def __init__(
        self,
        pipeline: DetectionPipeline,
        detection_fps: float,
        roi: NormalizedROI | None = None,
        cv2_module: Any | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._detection_fps = detection_fps
        self._roi = roi or NormalizedROI()
        if cv2_module is None:
            import cv2

            cv2_module = cv2
        self._cv2 = cv2_module

    def run(self, video_path: Path, on_result: ResultHandler | None = None) -> OfflineRunSummary:
        capture = self._cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            capture.release()
            raise ValueError(f"Video could not be opened: {video_path.name}")
        source_fps = float(capture.get(self._cv2.CAP_PROP_FPS))
        if source_fps <= 0:
            source_fps = 25.0
        sampler = FrameSampler(self._detection_fps)
        frames_read = frames_sampled = detections = ocr_calls = valid_plates = 0
        try:
            while True:
                success, image = capture.read()
                if not success or image is None:
                    break
                frames_read += 1
                height, width = image.shape[:2]
                captured_ns = round((frames_read - 1) / source_fps * 1_000_000_000)
                frame = CameraFrame(image, captured_ns, frames_read, width, height)
                if not sampler.should_process(frame):
                    continue
                result = self._pipeline.process(0, frame, self._roi)
                frames_sampled += 1
                detections += result.detection_count
                ocr_calls += result.ocr_calls
                valid_plates += sum(candidate.valid_format for candidate in result.candidates)
                if on_result is not None:
                    on_result(result)
        finally:
            capture.release()
        return OfflineRunSummary(
            frames_read=frames_read,
            frames_sampled=frames_sampled,
            detections=detections,
            ocr_calls=ocr_calls,
            valid_plates=valid_plates,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Garage LPR on a recorded video")
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--detector-model", required=True)
    parser.add_argument("--ocr-model", required=True)
    parser.add_argument("--provider", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--detection-fps", type=float, default=5.0)
    parser.add_argument("--detector-output", choices=("xyxy", "yolo_v8"), default="xyxy")
    arguments = parser.parse_args()
    settings = RuntimeSettings(
        detector_model_path=arguments.detector_model,
        ocr_model_path=arguments.ocr_model,
        inference_provider=arguments.provider,
        detection_fps=arguments.detection_fps,
        detector_output_format=arguments.detector_output,
    )
    bundle = ProductionPipelineFactory(ONNXRuntimeSessionFactory()).create(settings)

    def print_result(result: DetectionPipelineResult) -> None:
        for candidate in result.candidates:
            print(
                json.dumps(
                    {"frame_sequence": result.frame_sequence, **asdict(candidate)},
                    ensure_ascii=False,
                )
            )

    summary = OfflineVideoRunner(bundle.pipeline, settings.detection_fps).run(
        arguments.video, print_result
    )
    print(json.dumps({"summary": asdict(summary)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
