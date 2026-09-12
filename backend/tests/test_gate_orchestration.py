from dataclasses import replace
from typing import cast

from garage_lpr.access.status import AuthorizationStatus
from garage_lpr.camera.domain import CameraRuntimeSnapshot, CameraRuntimeState
from garage_lpr.camera.manager import CameraManager
from garage_lpr.gate.contracts import GateCommandResult
from garage_lpr.gate.manager import GateManager
from garage_lpr.gate.orchestration import (
    GateOrchestrationOutcome,
    GateOrchestrator,
    GateTarget,
    GateTargetResolution,
)
from garage_lpr.recognition.service import (
    RecognitionBatch,
    RecognitionDecision,
    RecognitionOutcome,
)


class Resolver:
    def __init__(self, resolution: GateTargetResolution) -> None:
        self.resolution = resolution

    def resolve(self, vehicle_id: int, camera_id: int) -> GateTargetResolution:
        return self.resolution


class Cameras:
    def __init__(self, state: CameraRuntimeState) -> None:
        self.state = state

    def snapshot(self, camera_id: int) -> CameraRuntimeSnapshot:
        return CameraRuntimeSnapshot(camera_id, self.state, "test", 3, 0, 1)


class Gates:
    def __init__(self) -> None:
        self.open_calls = 0

    def open(self, gate_controller_id: int, timeout_seconds: float) -> GateCommandResult:
        self.open_calls += 1
        return GateCommandResult(True, "OPENED")


def _decision() -> RecognitionDecision:
    return RecognitionDecision(
        camera_id=3,
        track_id=9,
        plate="34ABC123",
        confidence=0.96,
        confirmations=3,
        authorization_status=AuthorizationStatus.AUTHORIZED,
        outcome=RecognitionOutcome.AUTHORIZED_PENDING_GATE,
        vehicle_id=7,
        reason="AUTHORIZED",
    )


def _orchestrator(
    gates: Gates,
    *,
    simulation: bool,
    camera_state: CameraRuntimeState = CameraRuntimeState.CONNECTED,
    resolution: GateTargetResolution | None = None,
) -> GateOrchestrator:
    target = resolution or GateTargetResolution(GateTarget(11, 13), None, "resolved")
    return GateOrchestrator(
        Resolver(target),
        cast(GateManager, gates),
        cast(CameraManager, Cameras(camera_state)),
        simulation_mode=simulation,
        maintenance_mode=False,
        command_timeout_seconds=2,
    )


def test_simulation_mode_never_calls_gate_controller() -> None:
    gates = Gates()
    result = _orchestrator(gates, simulation=True).process_batch(
        RecognitionBatch((_decision(),), 1, 0)
    )[0]

    assert result.outcome is GateOrchestrationOutcome.SIMULATED_GATE_OPEN
    assert result.gate_controller_id == 13
    assert gates.open_calls == 0


def test_real_mode_uses_resolved_gate_once() -> None:
    gates = Gates()
    result = _orchestrator(gates, simulation=False).process(_decision())

    assert result is not None
    assert result.outcome is GateOrchestrationOutcome.GATE_OPEN_SUCCESS
    assert gates.open_calls == 1


def test_unhealthy_camera_and_missing_rule_fail_closed() -> None:
    unhealthy_gates = Gates()
    camera_result = _orchestrator(
        unhealthy_gates,
        simulation=False,
        camera_state=CameraRuntimeState.RECONNECTING,
    ).process(_decision())
    missing_gates = Gates()
    rule_result = _orchestrator(
        missing_gates,
        simulation=False,
        resolution=GateTargetResolution(
            None,
            GateOrchestrationOutcome.ACCESS_RULE_NOT_FOUND,
            "missing",
        ),
    ).process(_decision())

    assert camera_result is not None
    assert camera_result.outcome is GateOrchestrationOutcome.CAMERA_UNHEALTHY
    assert rule_result is not None
    assert rule_result.outcome is GateOrchestrationOutcome.ACCESS_RULE_NOT_FOUND
    assert unhealthy_gates.open_calls == 0
    assert missing_gates.open_calls == 0


def test_non_gate_ready_recognition_is_ignored() -> None:
    gates = Gates()
    decision = _decision()
    denied = replace(
        decision,
        authorization_status=AuthorizationStatus.UNAUTHORIZED,
        outcome=RecognitionOutcome.DENIED,
        vehicle_id=None,
    )

    assert _orchestrator(gates, simulation=False).process(denied) is None
    assert gates.open_calls == 0
