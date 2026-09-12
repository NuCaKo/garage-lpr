from threading import Event

from garage_lpr.gate.contracts import GateCommandResult, GateState
from garage_lpr.gate.domain import GateRuntimeConfiguration
from garage_lpr.gate.factory import GateControllerFactory
from garage_lpr.gate.manager import GateCommandExecutor, GateManager
from garage_lpr.gate.mock import MockGateController


def test_mock_gate_supports_pulse_and_explicit_close() -> None:
    controller = MockGateController(pulse_ms=500)

    assert controller.health_check()
    assert controller.status() is GateState.CLOSED
    assert controller.open().accepted
    assert controller.status() is GateState.OPEN
    assert controller.open_calls == 1
    assert controller.close().accepted
    assert controller.status() is GateState.CLOSED


class BlockingController:
    def __init__(self) -> None:
        self.release = Event()
        self.calls = 0

    def open(self) -> GateCommandResult:
        self.calls += 1
        self.release.wait()
        return GateCommandResult(True, "LATE_OPEN")

    def close(self) -> GateCommandResult:
        return GateCommandResult(True, "CLOSED")

    def status(self) -> GateState:
        return GateState.CLOSED

    def health_check(self) -> bool:
        return True


def test_gate_executor_timeout_poison_blocks_repeated_commands() -> None:
    executor = GateCommandExecutor()
    controller = BlockingController()
    try:
        first = executor.open(controller, timeout_seconds=0.01)
        second = executor.open(controller, timeout_seconds=0.01)

        assert not first.accepted
        assert first.detail == "GATE_COMMAND_TIMEOUT"
        assert not second.accepted
        assert second.detail == "GATE_EXECUTOR_POISONED"
        assert executor.poisoned
        assert controller.calls == 1
    finally:
        controller.release.set()
        executor.shutdown()


class BlockingControllerFactory(GateControllerFactory):
    def __init__(self, controller: BlockingController) -> None:
        self._controller = controller

    def create(self, configuration: GateRuntimeConfiguration) -> BlockingController:
        return self._controller


def test_gate_manager_reports_unhealthy_after_command_timeout() -> None:
    controller = BlockingController()
    manager = GateManager(BlockingControllerFactory(controller))
    manager.apply(
        GateRuntimeConfiguration(
            gate_controller_id=7,
            name="Blocking gate",
            controller_type="MOCK",
            pulse_ms=500,
            configuration={},
        )
    )
    try:
        result = manager.open(7, timeout_seconds=0.01)
        snapshot = manager.snapshot(7)

        assert not result.accepted
        assert result.detail == "GATE_COMMAND_TIMEOUT"
        assert not snapshot.healthy
        assert snapshot.state is GateState.UNAVAILABLE
        assert "poisoned" in snapshot.detail
    finally:
        controller.release.set()
        manager.shutdown()
