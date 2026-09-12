from dataclasses import dataclass

from garage_lpr.gate.contracts import GateState


@dataclass(frozen=True, slots=True)
class GateRuntimeConfiguration:
    gate_controller_id: int
    name: str
    controller_type: str
    pulse_ms: int
    configuration: dict[str, object]


@dataclass(frozen=True, slots=True)
class GateRuntimeSnapshot:
    gate_controller_id: int
    state: GateState
    healthy: bool
    detail: str
