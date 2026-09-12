from typing import Any

import numpy as np

from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.domain import NormalizedROI
from garage_lpr.detection.contracts import BoundingBox, PlateDetection
from garage_lpr.detection.pipeline import DetectionPipeline
from garage_lpr.ocr.contracts import OCRResult
from garage_lpr.ocr.normalizer import TurkishPlateNormalizer


class Detector:
    def __init__(self, detections: tuple[PlateDetection, ...]) -> None:
        self.detections = detections
        self.received_shape: tuple[int, ...] | None = None

    def detect(self, frame: Any) -> tuple[PlateDetection, ...]:
        self.received_shape = frame.shape
        return self.detections


class OCR:
    def __init__(self) -> None:
        self.received_shapes: list[tuple[int, ...]] = []

    def recognize(self, plate_crop: Any) -> OCRResult:
        self.received_shapes.append(plate_crop.shape)
        return OCRResult("34 A8C 123", 0.93, 4.2)


def test_pipeline_runs_ocr_only_on_plate_crop_inside_roi() -> None:
    detector = Detector((PlateDetection(BoundingBox(10, 5, 70, 30), 0.91),))
    ocr = OCR()
    pipeline = DetectionPipeline(detector, ocr, TurkishPlateNormalizer())
    frame = CameraFrame(np.zeros((100, 200, 3), dtype=np.uint8), 1, 8, 200, 100)

    result = pipeline.process(
        camera_id=4,
        frame=frame,
        roi=NormalizedROI(x=0.25, y=0.2, width=0.5, height=0.5),
    )

    assert detector.received_shape == (50, 100, 3)
    assert ocr.received_shapes == [(25, 60, 3)]
    assert result.ocr_calls == 1
    assert result.candidates[0].normalized_text == "34ABC123"
    assert result.candidates[0].box == BoundingBox(60, 25, 120, 50)


def test_pipeline_never_calls_ocr_when_plate_is_absent() -> None:
    detector = Detector(())
    ocr = OCR()
    pipeline = DetectionPipeline(detector, ocr, TurkishPlateNormalizer())
    frame = CameraFrame(np.zeros((100, 200, 3), dtype=np.uint8), 1, 1, 200, 100)

    result = pipeline.process(1, frame, NormalizedROI())

    assert result.detection_count == 0
    assert result.ocr_calls == 0
    assert ocr.received_shapes == []
