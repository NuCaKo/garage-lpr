from sqlalchemy import select
from sqlalchemy.orm import Session

from garage_lpr.database.models import GateControllerConfig


class GateControllerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[GateControllerConfig]:
        return list(
            self._session.scalars(
                select(GateControllerConfig).order_by(
                    GateControllerConfig.name, GateControllerConfig.id
                )
            )
        )

    def list_active(self) -> list[GateControllerConfig]:
        return list(
            self._session.scalars(
                select(GateControllerConfig)
                .where(GateControllerConfig.active.is_(True))
                .order_by(GateControllerConfig.id)
            )
        )

    def get(self, gate_controller_id: int) -> GateControllerConfig | None:
        return self._session.get(GateControllerConfig, gate_controller_id)

    def add(self, gate: GateControllerConfig) -> GateControllerConfig:
        self._session.add(gate)
        self._session.commit()
        self._session.refresh(gate)
        return gate

    def save(self, gate: GateControllerConfig) -> GateControllerConfig:
        self._session.commit()
        self._session.refresh(gate)
        return gate

    def delete(self, gate: GateControllerConfig) -> None:
        self._session.delete(gate)
        self._session.commit()
