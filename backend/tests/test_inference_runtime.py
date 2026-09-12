from pathlib import Path
from types import SimpleNamespace

import pytest

from garage_lpr.inference.runtime import (
    InferenceConfigurationError,
    ONNXRuntimeSessionFactory,
)


def _factory_with_providers(providers: list[str]) -> ONNXRuntimeSessionFactory:
    factory = object.__new__(ONNXRuntimeSessionFactory)
    factory._ort = SimpleNamespace(get_available_providers=lambda: providers)  # type: ignore[attr-defined]
    factory._intra_op_threads = 1  # type: ignore[attr-defined]
    return factory


def test_auto_provider_prefers_cuda_and_cpu_is_explicit_fallback() -> None:
    factory = _factory_with_providers(["CPUExecutionProvider", "CUDAExecutionProvider"])

    assert factory.selected_provider("auto") == "CUDAExecutionProvider"
    assert factory.selected_provider("cpu") == "CPUExecutionProvider"


def test_explicit_cuda_fails_closed_when_provider_is_unavailable() -> None:
    factory = _factory_with_providers(["CPUExecutionProvider"])

    with pytest.raises(InferenceConfigurationError, match="unavailable"):
        factory.selected_provider("cuda")
    with pytest.raises(InferenceConfigurationError, match="missing"):
        factory.create(Path("missing-model.onnx"), "auto")
