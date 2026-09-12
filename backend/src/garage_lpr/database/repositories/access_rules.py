from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from garage_lpr.database.models import AccessRule


class AccessRuleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[AccessRule]:
        return list(
            self._session.scalars(select(AccessRule).order_by(AccessRule.name, AccessRule.id))
        )

    def get(self, rule_id: int) -> AccessRule | None:
        return self._session.get(AccessRule, rule_id)

    def applicable(self, vehicle_id: int, camera_id: int) -> list[AccessRule]:
        statement = (
            select(AccessRule)
            .where(
                AccessRule.vehicle_id == vehicle_id,
                AccessRule.active.is_(True),
                or_(AccessRule.camera_id == camera_id, AccessRule.camera_id.is_(None)),
            )
            .order_by(AccessRule.camera_id.desc(), AccessRule.id)
        )
        return list(self._session.scalars(statement))

    def duplicate_exists(
        self,
        vehicle_id: int,
        camera_id: int | None,
        gate_controller_id: int,
        excluding_id: int | None = None,
    ) -> bool:
        camera_condition = (
            AccessRule.camera_id.is_(None)
            if camera_id is None
            else AccessRule.camera_id == camera_id
        )
        statement = select(AccessRule.id).where(
            AccessRule.vehicle_id == vehicle_id,
            camera_condition,
            AccessRule.gate_controller_id == gate_controller_id,
        )
        if excluding_id is not None:
            statement = statement.where(AccessRule.id != excluding_id)
        return self._session.scalar(statement.limit(1)) is not None

    def add(self, rule: AccessRule) -> AccessRule:
        self._session.add(rule)
        self._session.commit()
        self._session.refresh(rule)
        return rule

    def save(self, rule: AccessRule) -> AccessRule:
        self._session.commit()
        self._session.refresh(rule)
        return rule

    def delete(self, rule: AccessRule) -> None:
        self._session.delete(rule)
        self._session.commit()
