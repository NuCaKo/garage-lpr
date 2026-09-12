from dataclasses import dataclass
from time import perf_counter

from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.domain import NormalizedROI
from garage_lpr.detection.contracts import BoundingBox, PlateDetector
from garage_lpr.ocr.contracts import OCRProvider
from garage_lpr.ocr.normalizer import TurkishPlateNormalizer


@dataclass(frozen=True, slots=True)
class DetectionPipelineConfiguration:
    max_plates_per_frame: int = 3
    minimum_crop_width: int = 24
    minimum_crop_height: int = 12


@dataclass(frozen=True, slots=True)
class PlateRecognitionCandidate:
    box: BoundingBox
    detection_confidence: float
    raw_text: str
    normalized_text: str
    ocr_confidence: float
    valid_format: bool
    normalization_corrections: tuple[str, ...]
    ocr_processing_time_ms: float


@dataclass(frozen=True, slots=True)
class DetectionPipelineResult:
    camera_id: int
    frame_sequence: int
    candidates: tuple[PlateRecognitionCandidate, ...]
    detection_count: int
    ocr_calls: int
    detection_latency_ms: float
    total_ocr_latency_ms: float
    total_latency_ms: float


class DetectionPipeline:
    """Runs detector on ROI and OCR only on bounded plate crops."""

    def __init__(
        self,
        detector: PlateDetector,
        ocr: OCRProvider,
        normalizer: TurkishPlateNormalizer,
        configuration: DetectionPipelineConfiguration | None = None,
    ) -> None:
        self._detector = detector
        self._ocr = ocr
        self._normalizer = normalizer
        self._configuration = configuration or DetectionPipelineConfiguration()

    def process(
        self,
        camera_id: int,
        frame: CameraFrame,
        roi: NormalizedROI,
    ) -> DetectionPipelineResult:
        started = perf_counter()
        image = frame.image
        roi_image, offset_x, offset_y = _crop_roi(image, roi)
        detection_started = perf_counter()
        detections = sorted(
            self._detector.detect(roi_image),
            key=lambda item: item.confidence,
            reverse=True,
        )[: self._configuration.max_plates_per_frame]
        detection_latency_ms = _elapsed_ms(detection_started)
        candidates: list[PlateRecognitionCandidate] = []
        total_ocr_latency_ms = 0.0
        for detection in detections:
            crop, box = self._plate_crop(roi_image, detection.box, offset_x, offset_y)
            if crop is None:
                continue
            ocr_result = self._ocr.recognize(crop)
            total_ocr_latency_ms += ocr_result.processing_time_ms
            normalized = self._normalizer.normalize(ocr_result.text)
            candidates.append(
                PlateRecognitionCandidate(
                    box=box,
                    detection_confidence=detection.confidence,
                    raw_text=ocr_result.text,
                    normalized_text=normalized.text,
                    ocr_confidence=ocr_result.confidence,
                    valid_format=normalized.valid_format,
                    normalization_corrections=normalized.corrections,
                    ocr_processing_time_ms=ocr_result.processing_time_ms,
                )
            )
        return DetectionPipelineResult(
            camera_id=camera_id,
            frame_sequence=frame.sequence,
            candidates=tuple(candidates),
            detection_count=len(detections),
            ocr_calls=len(candidates),
            detection_latency_ms=detection_latency_ms,
            total_ocr_latency_ms=round(total_ocr_latency_ms, 2),
            total_latency_ms=_elapsed_ms(started),
        )

    def _plate_crop(
        self,
        roi_image: object,
        relative_box: BoundingBox,
        offset_x: int,
        offset_y: int,
    ) -> tuple[object | None, BoundingBox]:
        height, width = roi_image.shape[:2]  # type: ignore[attr-defined]
        x1 = min(width, max(0, int(relative_box.x1)))
        y1 = min(height, max(0, int(relative_box.y1)))
        x2 = min(width, max(0, int(relative_box.x2 + 0.999)))
        y2 = min(height, max(0, int(relative_box.y2 + 0.999)))
        full_box = BoundingBox(x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y)
        if (
            x2 - x1 < self._configuration.minimum_crop_width
            or y2 - y1 < self._configuration.minimum_crop_height
        ):
            return None, full_box
        return roi_image[y1:y2, x1:x2], full_box  # type: ignore[index]


def _crop_roi(image: object, roi: NormalizedROI) -> tuple[object, int, int]:
    height, width = image.shape[:2]  # type: ignore[attr-defined]
    x1 = min(width - 1, max(0, round(roi.x * width)))
    y1 = min(height - 1, max(0, round(roi.y * height)))
    x2 = min(width, max(x1 + 1, round((roi.x + roi.width) * width)))
    y2 = min(height, max(y1 + 1, round((roi.y + roi.height) * height)))
    return image[y1:y2, x1:x2], x1, y1  # type: ignore[index]


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)
