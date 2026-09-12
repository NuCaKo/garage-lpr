from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest

from garage_lpr.ocr.onnx_ocr import ONNXCTCOCRProvider, ONNXOCRConfiguration


class Input:
    name = "plate"

    def __init__(self, shape: list[int] | None = None) -> None:
        self.shape = shape or [1, 1, 48, 160]


class OCRSession:
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
        self.last_tensor = input_feed["plate"]
        return [self.output]


def test_ctc_ocr_collapses_repeats_and_blank_tokens() -> None:
    logits = np.full((1, 7, 4), -8.0, dtype=np.float32)
    for time_index, class_index in enumerate([1, 1, 0, 2, 0, 3, 3]):
        logits[0, time_index, class_index] = 8.0
    session = OCRSession(logits)
    provider = ONNXCTCOCRProvider(
        session,
        ONNXOCRConfiguration(charset="AB1", input_width=160, input_height=48),
    )

    result = provider.recognize(np.zeros((32, 100, 3), dtype=np.uint8))

    assert result.text == "AB1"
    assert result.confidence == pytest.approx(1.0, abs=0.001)
    assert result.processing_time_ms >= 0
    assert session.last_tensor is not None
    assert session.last_tensor.shape == (1, 1, 48, 160)
    assert session.last_tensor.dtype == np.float32


def test_ctc_ocr_rejects_charset_output_mismatch() -> None:
    session = OCRSession(np.zeros((1, 3, 8), dtype=np.float32))
    provider = ONNXCTCOCRProvider(session, ONNXOCRConfiguration(charset="AB1"))

    with pytest.raises(ValueError, match="class count"):
        provider.recognize(np.zeros((32, 100, 3), dtype=np.uint8))


def test_ctc_ocr_rejects_model_input_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="configured dimensions"):
        ONNXCTCOCRProvider(
            OCRSession(
                np.zeros((1, 3, 4), dtype=np.float32),
                input_shape=[1, 1, 32, 128],
            ),
            ONNXOCRConfiguration(),
        )
