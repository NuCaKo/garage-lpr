import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from garage_lpr.access.status import AuthorizationStatus
from garage_lpr.camera.domain import CameraRuntimeState
from garage_lpr.camera.manager import CameraManager
from garage_lpr.database.repositories.access_rules import AccessRuleRepository
from garage_lpr.database.repositories.gates import GateControllerRepository
from garage_lpr.gate.manager import GateManager
from garage_lpr.recognition.service import (
    RecognitionBatch,
    RecognitionDecision,
    RecognitionOutcome,
)


class GateOrchestrationOutcome(StrEnum):
    SIMULATED_GATE_OPEN = "SIMULATED_GATE_OPEN"
    GATE_OPEN_SUCCESS = "GATE_OPEN_SUCCESS"
    GATE_OPEN_FAILED = "GATE_OPEN_FAILED"
    CAMERA_UNHEALTHY = "CAMERA_UNHEALTHY"
    ACCESS_RULE_NOT_FOUND = "ACCESS_RULE_NOT_FOUND"
    ACCESS_RULE_AMBIGUOUS = "ACCESS_RULE_AMBIGUOUS"
    GATE_DISABLED = "GATE_DISABLED"
    MAINTENANCE_BLOCKED = "MAINTENANCE_BLOCKED"


@dataclass(frozen=True, slots=True)
class GateTarget:
    access_rule_id: int
    gate_controller_id: int


@dataclass(frozen=True, slots=True)
class GateTargetResolution:
    target: GateTarget | None
    outcome: GateOrchestrationOutcome | None
    detail: str


@dataclass(frozen=True, slots=True)
class GateOrchestrationResult:
    camera_id: int
    vehicle_id: int
    plate: str
    outcome: GateOrchestrationOutcome
    detail: str
    access_rule_id: int | None = None
    gate_controller_id: int | None = None


class GateTargetResolver(Protocol):
    def resolve(self, vehicle_id: int, camera_id: int) -> GateTargetResolution: ...


class DatabaseGateTargetResolver:
    """Resolves exact-camera rules before optional all-camera fallback rules."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._logger = logging.getLogger("garage_lpr.gate.rules")

    def resolve(self, vehicle_id: int, camera_id: int) -> GateTargetResolution:
        session: Session | None = None
        try:
            session = self._session_factory()
            rules = AccessRuleRepository(session).applicable(vehicle_id, camera_id)
            exact = [rule for rule in rules if rule.camera_id == camera_id]
            fallback = [rule for rule in rules if rule.camera_id is None]
            candidates = exact or fallback
            if not candidates:
                return GateTargetResolution(
                    None,
                    GateOrchestrationOutcome.ACCESS_RULE_NOT_FOUND,
                    "No active access rule matches the vehicle and camera",
                )
            if len(candidates) != 1:
                return GateTargetResolution(
                    None,
                    GateOrchestrationOutcome.ACCESS_RULE_AMBIGUOUS,
                    "Multiple active access rules match the same priority",
                )
            rule = candidates[0]
            gate = GateControllerRepository(session).get(rule.gate_controller_id)
            if gate is None or not gate.active:
                return GateTargetResolution(
                    None,
                    GateOrchestrationOutcome.GATE_DISABLED,
                    "Mapped gate controller is missing or disabled",
                )
            return GateTargetResolution(
                GateTarget(rule.id, rule.gate_controller_id), None, "Access rule resolved"
            )
        except SQLAlchemyError as error:
            if session is not None:
                session.rollback()
            self._logger.error(
                "gate_rule_database_unavailable",
                extra={"metadata": {"error_type": type(error).__name__}},
            )
            return GateTargetResolution(
                None,
                GateOrchestrationOutcome.ACCESS_RULE_NOT_FOUND,
                "Access rule database is unavailable",
            )
        finally:
            if session is not None:
                session.close()


class GateOrchestrator:
    """The only service allowed to translate recognition intent into gate open."""

    def __init__(
        self,
        resolver: GateTargetResolver,
        gate_manager: GateManager,
        camera_manager: CameraManager,
        simulation_mode: bool,
        maintenance_mode: bool,
        command_timeout_seconds: float,
    ) -> None:
        self._resolver = resolver
        self._gate_manager = gate_manager
        self._camera_manager = camera_manager
        self._simulation_mode = simulation_mode
        self._maintenance_mode = maintenance_mode
        self._command_timeout_seconds = command_timeout_seconds
        self._logger = logging.getLogger("garage_lpr.gate.orchestration")

    def process_batch(self, batch: RecognitionBatch) -> tuple[GateOrchestrationResult, ...]:
        return tuple(
            result for decision in batch.decisions if (result := self.process(decision)) is not None
        )

    def process(self, decision: RecognitionDecision) -> GateOrchestrationResult | None:
        if (
            decision.outcome is not RecognitionOutcome.AUTHORIZED_PENDING_GATE
            or decision.authorization_status is not AuthorizationStatus.AUTHORIZED
            or decision.vehicle_id is None
        ):
            return None
        if self._maintenance_mode:
            return self._finalize(
                self._result(
                    decision,
                    GateOrchestrationOutcome.MAINTENANCE_BLOCKED,
                    "Maintenance mode blocks gate commands",
                )
            )
        camera = self._camera_manager.snapshot(decision.camera_id)
        if camera.state is not CameraRuntimeState.CONNECTED:
            return self._finalize(
                self._result(
                    decision,
                    GateOrchestrationOutcome.CAMERA_UNHEALTHY,
                    "Camera is not connected at command time",
                )
            )
        resolution = self._resolver.resolve(decision.vehicle_id, decision.camera_id)
        if resolution.target is None:
            return self._finalize(
                self._result(
                    decision,
                    resolution.outcome or GateOrchestrationOutcome.ACCESS_RULE_NOT_FOUND,
                    resolution.detail,
                )
            )
        target = resolution.target
        if self._simulation_mode:
            result = self._result(
                decision,
                GateOrchestrationOutcome.SIMULATED_GATE_OPEN,
                "Simulation mode: no controller command was sent",
                target,
            )
        else:
            command = self._gate_manager.open(
                target.gate_controller_id, self._command_timeout_seconds
            )
            result = self._result(
                decision,
                (
                    GateOrchestrationOutcome.GATE_OPEN_SUCCESS
                    if command.accepted
                    else GateOrchestrationOutcome.GATE_OPEN_FAILED
                ),
                command.detail,
                target,
            )
        return self._finalize(result)

    def _finalize(self, result: GateOrchestrationResult) -> GateOrchestrationResult:
        log = (
            self._logger.info
            if result.outcome
            in {
                GateOrchestrationOutcome.GATE_OPEN_SUCCESS,
                GateOrchestrationOutcome.SIMULATED_GATE_OPEN,
            }
            else self._logger.warning
        )
        log(
            result.outcome.value.lower(),
            extra={
                "metadata": {
                    "camera_id": result.camera_id,
                    "vehicle_id": result.vehicle_id,
                    "gate_controller_id": result.gate_controller_id,
                    "access_rule_id": result.access_rule_id,
                    "plate": result.plate,
                }
            },
        )
        return result

    @staticmethod
    def _result(
        decision: RecognitionDecision,
        outcome: GateOrchestrationOutcome,
        detail: str,
        target: GateTarget | None = None,
    ) -> GateOrchestrationResult:
        if decision.vehicle_id is None:
            raise ValueError("Authorized decision must contain a vehicle id")
        return GateOrchestrationResult(
            camera_id=decision.camera_id,
            vehicle_id=decision.vehicle_id,
            plate=decision.plate,
            outcome=outcome,
            detail=detail,
            access_rule_id=target.access_rule_id if target else None,
            gate_controller_id=target.gate_controller_id if target else None,
        )
