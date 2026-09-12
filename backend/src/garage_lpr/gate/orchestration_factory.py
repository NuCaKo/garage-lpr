from collections.abc import Callable

from sqlalchemy.orm import Session

from garage_lpr.camera.manager import CameraManager
from garage_lpr.config.settings import RuntimeSettings
from garage_lpr.gate.manager import GateManager
from garage_lpr.gate.orchestration import DatabaseGateTargetResolver, GateOrchestrator


class GateOrchestratorFactory:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        gate_manager: GateManager,
        camera_manager: CameraManager,
    ) -> None:
        self._session_factory = session_factory
        self._gate_manager = gate_manager
        self._camera_manager = camera_manager

    def create(self, settings: RuntimeSettings) -> GateOrchestrator:
        return GateOrchestrator(
            resolver=DatabaseGateTargetResolver(self._session_factory),
            gate_manager=self._gate_manager,
            camera_manager=self._camera_manager,
            simulation_mode=settings.simulation_mode,
            maintenance_mode=settings.maintenance_mode,
            command_timeout_seconds=settings.gate_command_timeout_seconds,
        )
