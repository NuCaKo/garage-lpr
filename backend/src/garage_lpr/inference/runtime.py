from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, Protocol

InferenceProvider = Literal["auto", "cpu", "cuda"]


class InferenceConfigurationError(RuntimeError):
    pass


class TensorMetadata(Protocol):
    name: str
    shape: list[Any]


class InferenceSession(Protocol):
    def get_inputs(self) -> Sequence[TensorMetadata]: ...

    def get_providers(self) -> list[str]: ...

    def run(self, output_names: None, input_feed: dict[str, Any]) -> list[Any]: ...


class SessionFactory(Protocol):
    def create(self, model_path: Path, provider: InferenceProvider) -> InferenceSession: ...

    def selected_provider(self, provider: InferenceProvider) -> str: ...


class ONNXRuntimeSessionFactory:
    """Creates conservative, sequential ORT sessions with explicit provider order."""

    def __init__(self, intra_op_threads: int = 1) -> None:
        import onnxruntime as ort  # type: ignore[import-untyped]

        self._ort = ort
        self._intra_op_threads = intra_op_threads

    def selected_provider(self, provider: InferenceProvider) -> str:
        available = set(self._ort.get_available_providers())
        if provider == "cuda":
            if "CUDAExecutionProvider" not in available:
                raise InferenceConfigurationError("CUDA execution provider is unavailable")
            return "CUDAExecutionProvider"
        if provider == "auto" and "CUDAExecutionProvider" in available:
            return "CUDAExecutionProvider"
        if "CPUExecutionProvider" not in available:
            raise InferenceConfigurationError("CPU execution provider is unavailable")
        return "CPUExecutionProvider"

    def create(self, model_path: Path, provider: InferenceProvider) -> InferenceSession:
        if not model_path.is_file():
            raise InferenceConfigurationError(f"Model file is missing: {model_path.name}")
        selected = self.selected_provider(provider)
        providers = [selected]
        if selected == "CUDAExecutionProvider":
            providers.append("CPUExecutionProvider")
        options = self._ort.SessionOptions()
        options.intra_op_num_threads = self._intra_op_threads
        options.inter_op_num_threads = 1
        options.execution_mode = self._ort.ExecutionMode.ORT_SEQUENTIAL
        options.graph_optimization_level = self._ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        return self._ort.InferenceSession(
            str(model_path),
            sess_options=options,
            providers=providers,
        )
