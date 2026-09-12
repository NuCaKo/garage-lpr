from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class OCRResult:
    text: str
    confidence: float
    processing_time_ms: float


class OCRProvider(Protocol):
    def recognize(self, plate_crop: Any) -> OCRResult: ...
