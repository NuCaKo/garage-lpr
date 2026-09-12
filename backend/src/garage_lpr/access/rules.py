from typing import cast

from garage_lpr.database.models import AccessRule
from garage_lpr.database.repositories.access_rules import AccessRuleRepository
from garage_lpr.database.repositories.cameras import CameraRepository
from garage_lpr.database.repositories.gates import GateControllerRepository
from garage_lpr.database.repositories.vehicles import VehicleRepository


class AccessRuleConflictError(ValueError):
    pass


class AccessRuleReferenceError(ValueError):
    pass


class AccessRuleService:
    def __init__(
        self,
        repository: AccessRuleRepository,
        vehicles: VehicleRepository,
        cameras: CameraRepository,
        gates: GateControllerRepository,
    ) -> None:
        self._repository = repository
        self._vehicles = vehicles
        self._cameras = cameras
        self._gates = gates

    def list_all(self) -> list[AccessRule]:
        return self._repository.list_all()

    def get(self, rule_id: int) -> AccessRule | None:
        return self._repository.get(rule_id)

    def create(self, values: dict[str, object]) -> AccessRule:
        self._validate(values)
        return self._repository.add(AccessRule(**values))

    def update(self, rule: AccessRule, values: dict[str, object]) -> AccessRule:
        self._validate(values, excluding_id=rule.id)
        for name, value in values.items():
            setattr(rule, name, value)
        return self._repository.save(rule)

    def delete(self, rule: AccessRule) -> None:
        self._repository.delete(rule)

    def _validate(self, values: dict[str, object], excluding_id: int | None = None) -> None:
        vehicle_id = cast(int, values["vehicle_id"])
        gate_controller_id = cast(int, values["gate_controller_id"])
        camera_value = values.get("camera_id")
        camera_id = cast(int, camera_value) if camera_value is not None else None
        if self._vehicles.get(vehicle_id) is None:
            raise AccessRuleReferenceError("Vehicle not found")
        if camera_id is not None and self._cameras.get(camera_id) is None:
            raise AccessRuleReferenceError("Camera not found")
        if self._gates.get(gate_controller_id) is None:
            raise AccessRuleReferenceError("Gate controller not found")
        if self._repository.duplicate_exists(
            vehicle_id,
            camera_id,
            gate_controller_id,
            excluding_id=excluding_id,
        ):
            raise AccessRuleConflictError("Equivalent access rule already exists")
