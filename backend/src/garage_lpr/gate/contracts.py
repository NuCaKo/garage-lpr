from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class GateState(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class GateCommandResult:
    accepted: bool
    detail: str


class GateController(Protocol):
    def open(self) -> GateCommandResult: ...

    def close(self) -> GateCommandResult: ...

    def status(self) -> GateState: ...

    def health_check(self) -> bool: ...
