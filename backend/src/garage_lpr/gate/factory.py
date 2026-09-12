from garage_lpr.gate.contracts import GateController
from garage_lpr.gate.domain import GateRuntimeConfiguration
from garage_lpr.gate.mock import MockGateController


class UnsupportedGateControllerError(ValueError):
    pass


class GateControllerFactory:
    """Builds supported adapters without leaking persistence models into drivers."""

    def create(self, configuration: GateRuntimeConfiguration) -> GateController:
        if configuration.controller_type == "MOCK":
            return MockGateController(pulse_ms=configuration.pulse_ms)
        raise UnsupportedGateControllerError(
            f"Gate controller type {configuration.controller_type!r} is not implemented"
        )
