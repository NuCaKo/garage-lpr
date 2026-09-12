from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from garage_lpr.detection.contracts import BoundingBox, PlateDetection
from garage_lpr.inference.runtime import InferenceSession


@dataclass(frozen=True, slots=True)
class ONNXDetectorConfiguration:
    input_width: int = 640
    input_height: int = 640
    confidence_threshold: float = 0.70
    iou_threshold: float = 0.45
    output_format: Literal["xyxy", "yolo_v8"] = "xyxy"


class ONNXPlateDetector:
    """Small adapter for explicit XYXY or YOLOv8-style ONNX detector outputs."""

    def __init__(
        self,
        session: InferenceSession,
        configuration: ONNXDetectorConfiguration,
        cv2_module: Any | None = None,
    ) -> None:
        if len(session.get_inputs()) != 1:
            raise ValueError("Detector model must have exactly one input")
        if not 0 < configuration.confidence_threshold <= 1:
            raise ValueError("Detector confidence threshold must be within (0, 1]")
        self._session = session
        self._configuration = configuration
        input_metadata = session.get_inputs()[0]
        _validate_input_shape(
            input_metadata.shape,
            (3, configuration.input_height, configuration.input_width),
            "Detector",
        )
        self._input_name = input_metadata.name
        if cv2_module is None:
            import cv2

            cv2_module = cv2
        self._cv2 = cv2_module

    @property
    def provider(self) -> str:
        providers = self._session.get_providers()
        return providers[0] if providers else "UnknownExecutionProvider"

    def detect(self, frame: Any) -> tuple[PlateDetection, ...]:
        image = np.asarray(frame)
        if image.ndim != 3 or image.shape[2] < 3:
            raise ValueError("Detector input must be a BGR color image")
        tensor, scale, pad_x, pad_y = self._preprocess(image)
        outputs = self._session.run(None, {self._input_name: tensor})
        if not outputs:
            return ()
        candidates = self._decode(np.asarray(outputs[0]), scale, pad_x, pad_y, image.shape)
        return tuple(candidates[index] for index in self._nms(candidates))

    def _preprocess(
        self, image: np.ndarray[Any, Any]
    ) -> tuple[np.ndarray[Any, Any], float, int, int]:
        source_height, source_width = image.shape[:2]
        target_width = self._configuration.input_width
        target_height = self._configuration.input_height
        scale = min(target_width / source_width, target_height / source_height)
        resized_width = max(1, round(source_width * scale))
        resized_height = max(1, round(source_height * scale))
        resized = self._cv2.resize(
            image[:, :, :3],
            (resized_width, resized_height),
            interpolation=self._cv2.INTER_LINEAR,
        )
        pad_x = (target_width - resized_width) // 2
        pad_y = (target_height - resized_height) // 2
        canvas = np.full((target_height, target_width, 3), 114, dtype=np.uint8)
        canvas[pad_y : pad_y + resized_height, pad_x : pad_x + resized_width] = resized
        rgb = canvas[:, :, ::-1]
        tensor = np.ascontiguousarray(rgb.transpose(2, 0, 1)[None], dtype=np.float32)
        tensor /= 255.0
        return tensor, scale, pad_x, pad_y

    def _decode(
        self,
        output: np.ndarray[Any, Any],
        scale: float,
        pad_x: int,
        pad_y: int,
        source_shape: tuple[int, ...],
    ) -> list[PlateDetection]:
        rows = self._rows(output)
        detections: list[PlateDetection] = []
        source_height, source_width = source_shape[:2]
        for row in rows:
            decoded = self._decode_row(row)
            if decoded is None:
                continue
            x1, y1, x2, y2, confidence, class_id = decoded
            x1 = min(source_width, max(0.0, (x1 - pad_x) / scale))
            y1 = min(source_height, max(0.0, (y1 - pad_y) / scale))
            x2 = min(source_width, max(0.0, (x2 - pad_x) / scale))
            y2 = min(source_height, max(0.0, (y2 - pad_y) / scale))
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append(PlateDetection(BoundingBox(x1, y1, x2, y2), confidence, class_id))
        return detections

    def _rows(self, output: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        matrix = output[0] if output.ndim == 3 and output.shape[0] == 1 else output
        if matrix.ndim == 1 and self._configuration.output_format == "xyxy":
            matrix = matrix[None, :]
        if matrix.ndim != 2:
            raise ValueError("Detector output must reduce to a two-dimensional matrix")
        if self._configuration.output_format == "yolo_v8":
            if matrix.shape[0] < 5:
                raise ValueError("YOLOv8 output must contain box and class channels")
            return matrix.T
        if matrix.shape[1] < 6:
            raise ValueError("XYXY output rows must contain at least six values")
        return matrix

    def _decode_row(
        self, row: np.ndarray[Any, Any]
    ) -> tuple[float, float, float, float, float, int] | None:
        if self._configuration.output_format == "yolo_v8":
            class_scores = row[4:]
            class_id = int(np.argmax(class_scores))
            confidence = float(class_scores[class_id])
            center_x, center_y, width, height = (float(value) for value in row[:4])
            coordinates = (
                center_x - width / 2,
                center_y - height / 2,
                center_x + width / 2,
                center_y + height / 2,
            )
        else:
            coordinates = (
                float(row[0]),
                float(row[1]),
                float(row[2]),
                float(row[3]),
            )
            confidence = float(row[4])
            class_id = int(row[5])
        if not np.isfinite(confidence) or confidence < self._configuration.confidence_threshold:
            return None
        return (*coordinates, confidence, class_id)

    def _nms(self, detections: list[PlateDetection]) -> list[int]:
        ordered = sorted(
            range(len(detections)),
            key=lambda index: detections[index].confidence,
            reverse=True,
        )
        selected: list[int] = []
        while ordered:
            current = ordered.pop(0)
            selected.append(current)
            ordered = [
                candidate
                for candidate in ordered
                if _intersection_over_union(detections[current].box, detections[candidate].box)
                <= self._configuration.iou_threshold
            ]
        return selected


def _intersection_over_union(first: BoundingBox, second: BoundingBox) -> float:
    intersection_width = max(0.0, min(first.x2, second.x2) - max(first.x1, second.x1))
    intersection_height = max(0.0, min(first.y2, second.y2) - max(first.y1, second.y1))
    intersection = intersection_width * intersection_height
    first_area = max(0.0, first.x2 - first.x1) * max(0.0, first.y2 - first.y1)
    second_area = max(0.0, second.x2 - second.x1) * max(0.0, second.y2 - second.y1)
    union = first_area + second_area - intersection
    return intersection / union if union > 0 else 0.0


def _validate_input_shape(shape: list[Any], expected: tuple[int, int, int], name: str) -> None:
    if len(shape) != 4:
        raise ValueError(f"{name} input must be a four-dimensional NCHW tensor")
    for configured, actual in zip(expected, shape[1:], strict=True):
        if isinstance(actual, int) and actual > 0 and actual != configured:
            raise ValueError(f"{name} input shape does not match configured dimensions")
