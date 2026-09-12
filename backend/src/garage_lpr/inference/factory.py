from dataclasses import dataclass
from pathlib import Path

from garage_lpr.config.settings import RuntimeSettings, repository_root, runtime_root
from garage_lpr.detection.onnx_detector import (
    ONNXDetectorConfiguration,
    ONNXPlateDetector,
)
from garage_lpr.detection.pipeline import (
    DetectionPipeline,
    DetectionPipelineConfiguration,
)
from garage_lpr.inference.runtime import SessionFactory
from garage_lpr.ocr.normalizer import TurkishPlateNormalizer
from garage_lpr.ocr.onnx_ocr import ONNXCTCOCRProvider, ONNXOCRConfiguration


class ComponentInitializationError(RuntimeError):
    def __init__(self, component: str, detail: str) -> None:
        super().__init__(detail)
        self.component = component
        self.detail = detail


@dataclass(frozen=True, slots=True)
class PipelineBundle:
    pipeline: DetectionPipeline
    detector_provider: str
    ocr_provider: str


class ProductionPipelineFactory:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create(self, settings: RuntimeSettings) -> PipelineBundle:
        detector_path = _model_path(settings.detector_model_path)
        ocr_path = _model_path(settings.ocr_model_path)
        try:
            detector_session = self._session_factory.create(
                detector_path, settings.inference_provider
            )
        except Exception as error:
            raise ComponentInitializationError(
                "detector", f"Detector model could not be loaded: {detector_path.name}"
            ) from error
        try:
            ocr_session = self._session_factory.create(ocr_path, settings.inference_provider)
        except Exception as error:
            raise ComponentInitializationError(
                "ocr", f"OCR model could not be loaded: {ocr_path.name}"
            ) from error

        try:
            detector = ONNXPlateDetector(
                detector_session,
                ONNXDetectorConfiguration(
                    input_width=settings.detector_input_width,
                    input_height=settings.detector_input_height,
                    confidence_threshold=settings.detector_confidence_threshold,
                    iou_threshold=settings.detector_iou_threshold,
                    output_format=settings.detector_output_format,
                ),
            )
        except Exception as error:
            raise ComponentInitializationError(
                "detector", "Detector model contract is incompatible with its settings"
            ) from error
        try:
            ocr = ONNXCTCOCRProvider(
                ocr_session,
                ONNXOCRConfiguration(
                    charset=settings.ocr_charset,
                    input_width=settings.ocr_input_width,
                    input_height=settings.ocr_input_height,
                    input_channels=settings.ocr_input_channels,
                ),
            )
        except Exception as error:
            raise ComponentInitializationError(
                "ocr", "OCR model contract is incompatible with its settings"
            ) from error
        return PipelineBundle(
            pipeline=DetectionPipeline(
                detector,
                ocr,
                TurkishPlateNormalizer(),
                DetectionPipelineConfiguration(max_plates_per_frame=settings.max_plates_per_frame),
            ),
            detector_provider=detector.provider,
            ocr_provider=ocr.provider,
        )


def _model_path(configured: str) -> Path:
    path = Path(configured).expanduser()
    if path.is_absolute():
        return path
    writable_model = runtime_root() / path
    if writable_model.exists():
        return writable_model
    return repository_root() / path
