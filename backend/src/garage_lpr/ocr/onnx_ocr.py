from dataclasses import dataclass
from time import perf_counter
from typing import Any

import numpy as np

from garage_lpr.inference.runtime import InferenceSession
from garage_lpr.ocr.contracts import OCRResult


@dataclass(frozen=True, slots=True)
class ONNXOCRConfiguration:
    charset: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    input_width: int = 160
    input_height: int = 48
    input_channels: int = 1
    blank_index: int = 0


class ONNXCTCOCRProvider:
    """Fixed-size CRNN/CTC ONNX OCR adapter for plate crops only."""

    def __init__(
        self,
        session: InferenceSession,
        configuration: ONNXOCRConfiguration,
        cv2_module: Any | None = None,
    ) -> None:
        if len(session.get_inputs()) != 1:
            raise ValueError("OCR model must have exactly one input")
        if configuration.input_channels not in {1, 3}:
            raise ValueError("OCR input channels must be 1 or 3")
        if len(set(configuration.charset)) != len(configuration.charset):
            raise ValueError("OCR charset must not contain duplicate characters")
        if configuration.blank_index != 0:
            raise ValueError("This OCR adapter requires CTC blank index zero")
        self._session = session
        self._configuration = configuration
        input_metadata = session.get_inputs()[0]
        _validate_input_shape(
            input_metadata.shape,
            (
                configuration.input_channels,
                configuration.input_height,
                configuration.input_width,
            ),
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

    def recognize(self, plate_crop: Any) -> OCRResult:
        started = perf_counter()
        tensor = self._preprocess(np.asarray(plate_crop))
        outputs = self._session.run(None, {self._input_name: tensor})
        if not outputs:
            return OCRResult("", 0.0, _elapsed_ms(started))
        text, confidence = self._decode(np.asarray(outputs[0]))
        return OCRResult(text, confidence, _elapsed_ms(started))

    def _preprocess(self, image: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        if image.ndim not in {2, 3} or image.size == 0:
            raise ValueError("OCR input must be a non-empty plate crop")
        config = self._configuration
        if image.ndim == 3:
            grayscale = self._cv2.cvtColor(image[:, :, :3], self._cv2.COLOR_BGR2GRAY)
        else:
            grayscale = image
        source_height, source_width = grayscale.shape[:2]
        scale = min(config.input_width / source_width, config.input_height / source_height)
        width = max(1, round(source_width * scale))
        height = max(1, round(source_height * scale))
        resized = self._cv2.resize(
            grayscale,
            (width, height),
            interpolation=self._cv2.INTER_LINEAR,
        )
        canvas = np.zeros((config.input_height, config.input_width), dtype=np.uint8)
        offset_x = (config.input_width - width) // 2
        offset_y = (config.input_height - height) // 2
        canvas[offset_y : offset_y + height, offset_x : offset_x + width] = resized
        normalized = canvas.astype(np.float32) / 127.5 - 1.0
        if config.input_channels == 3:
            normalized = np.repeat(normalized[None], 3, axis=0)
        else:
            normalized = normalized[None]
        return np.ascontiguousarray(normalized[None], dtype=np.float32)

    def _decode(self, output: np.ndarray[Any, Any]) -> tuple[str, float]:
        logits = output[0] if output.ndim == 3 and output.shape[0] == 1 else output
        if logits.ndim != 2:
            raise ValueError("OCR output must be [1, time, classes] or [time, classes]")
        if logits.shape[1] != len(self._configuration.charset) + 1:
            raise ValueError("OCR output class count does not match configured charset")
        indices = np.argmax(logits, axis=1)
        emitted: list[str] = []
        confidences: list[float] = []
        previous: int | None = None
        for time_index, class_index_value in enumerate(indices):
            class_index = int(class_index_value)
            if class_index != self._configuration.blank_index and class_index != previous:
                charset_index = class_index - 1
                if charset_index < 0 or charset_index >= len(self._configuration.charset):
                    raise ValueError("OCR class index is outside the configured charset")
                emitted.append(self._configuration.charset[charset_index])
                confidences.append(_softmax_probability(logits[time_index], class_index))
            previous = class_index
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return "".join(emitted), round(confidence, 4)


def _softmax_probability(row: np.ndarray[Any, Any], index: int) -> float:
    shifted = row - np.max(row)
    exponents = np.exp(shifted)
    return float(exponents[index] / np.sum(exponents))


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)


def _validate_input_shape(shape: list[Any], expected: tuple[int, int, int]) -> None:
    if len(shape) != 4:
        raise ValueError("OCR input must be a four-dimensional NCHW tensor")
    for configured, actual in zip(expected, shape[1:], strict=True):
        if isinstance(actual, int) and actual > 0 and actual != configured:
            raise ValueError("OCR input shape does not match configured dimensions")
