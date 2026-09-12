import pytest
from pydantic import ValidationError

from garage_lpr.config.settings import RuntimeSettings


def test_runtime_settings_enforce_low_frequency_metrics() -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(metrics_poll_interval_seconds=1)


def test_runtime_settings_require_multiple_confirmations() -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(required_confirmations=1)


def test_runtime_settings_normalize_and_validate_model_contract_values() -> None:
    settings = RuntimeSettings(
        detector_model_path="  models/detector.onnx  ",
        ocr_charset="abcdef0123",
    )

    assert settings.detector_model_path == "models/detector.onnx"
    assert settings.ocr_charset == "ABCDEF0123"

    with pytest.raises(ValidationError):
        RuntimeSettings(ocr_charset="AABC012345")
