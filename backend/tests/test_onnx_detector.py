from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest

from garage_lpr.detection.onnx_detector import (
    ONNXDetectorConfiguration,
    ONNXPlateDetector,
)


class Input:
    name = "images"

    def __init__(self, shape: list[int] | None = None) -> None:
        self.shape = shape or [1, 3, 640, 640]


class DetectorSession:
    def __init__(
        self,
        output: np.ndarray[Any, Any],
        input_shape: list[int] | None = None,
    ) -> None:
        self.output = output
        self.input = Input(input_shape)
        self.last_tensor: np.ndarray[Any, Any] | None = None

    def get_inputs(self) -> Sequence[Input]:
        return [self.input]

    def get_providers(self) -> list[str]:
        return ["CPUExecutionProvider"]

    def run(self, output_names: None, input_feed: dict[str, Any]) -> list[Any]:
        self.last_tensor = input_feed["images"]
        return [self.output]


def test_xyxy_detector_letterboxes_maps_coordinates_and_applies_nms() -> None:
    output = np.array(
        [[[200, 220, 440, 300, 0.95, 0], [205, 222, 438, 298, 0.80, 0]]],
        dtype=np.float32,
    )
    session = DetectorSession(output)
    detector = ONNXPlateDetector(session, ONNXDetectorConfiguration())
    frame = np.zeros((160, 320, 3), dtype=np.uint8)

    detections = detector.detect(frame)

    assert len(detections) == 1
    assert detections[0].confidence == pytest.approx(0.95)
    assert detections[0].box.x1 == pytest.approx(100)
    assert detections[0].box.y1 == pytest.approx(30)
    assert detections[0].box.x2 == pytest.approx(220)
    assert detections[0].box.y2 == pytest.approx(70)
    assert session.last_tensor is not None
    assert session.last_tensor.shape == (1, 3, 640, 640)
    assert session.last_tensor.dtype == np.float32


def test_yolo_v8_decoder_uses_highest_class_score() -> None:
    output = np.array([[[320], [320], [200], [100], [0.1], [0.9]]], dtype=np.float32)
    detector = ONNXPlateDetector(
        DetectorSession(output),
        ONNXDetectorConfiguration(output_format="yolo_v8", confidence_threshold=0.7),
    )

    detection = detector.detect(np.zeros((640, 640, 3), dtype=np.uint8))[0]

    assert detection.class_id == 1
    assert detection.box.x1 == pytest.approx(220)
    assert detection.box.y1 == pytest.approx(270)


def test_detector_rejects_model_input_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="configured dimensions"):
        ONNXPlateDetector(
            DetectorSession(
                np.empty((1, 0, 6), dtype=np.float32),
                input_shape=[1, 3, 320, 320],
            ),
            ONNXDetectorConfiguration(),
        )
