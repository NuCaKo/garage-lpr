from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True, slots=True)
class PlateDetection:
    box: BoundingBox
    confidence: float
    class_id: int = 0


class PlateDetector(Protocol):
    def detect(self, frame: Any) -> tuple[PlateDetection, ...]: ...
