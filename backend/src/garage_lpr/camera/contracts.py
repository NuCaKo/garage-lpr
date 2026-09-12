from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CameraFrame:
    image: Any
    captured_monotonic_ns: int
    sequence: int
    width: int
    height: int


class CameraProvider(Protocol):
    def connect(self) -> None: ...

    def read(self) -> CameraFrame | None: ...

    def close(self) -> None: ...

    def healthy(self) -> bool: ...
