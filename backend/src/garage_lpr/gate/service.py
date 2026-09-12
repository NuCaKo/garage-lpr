from garage_lpr.database.models import GateControllerConfig
from garage_lpr.database.repositories.gates import GateControllerRepository
from garage_lpr.gate.domain import GateRuntimeConfiguration


class GateControllerService:
    def __init__(self, repository: GateControllerRepository) -> None:
        self._repository = repository

    def list_all(self) -> list[GateControllerConfig]:
        return self._repository.list_all()

    def get(self, gate_controller_id: int) -> GateControllerConfig | None:
        return self._repository.get(gate_controller_id)

    def create(self, values: dict[str, object]) -> GateControllerConfig:
        return self._repository.add(GateControllerConfig(**values))

    def update(self, gate: GateControllerConfig, values: dict[str, object]) -> GateControllerConfig:
        for name, value in values.items():
            setattr(gate, name, value)
        return self._repository.save(gate)

    def delete(self, gate: GateControllerConfig) -> None:
        self._repository.delete(gate)

    @staticmethod
    def runtime_configuration(gate: GateControllerConfig) -> GateRuntimeConfiguration:
        return GateRuntimeConfiguration(
            gate_controller_id=gate.id,
            name=gate.name,
            controller_type=gate.controller_type,
            pulse_ms=gate.pulse_ms,
            configuration=dict(gate.configuration or {}),
        )
