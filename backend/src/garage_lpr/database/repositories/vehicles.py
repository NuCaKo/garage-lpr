from sqlalchemy import select
from sqlalchemy.orm import Session

from garage_lpr.database.models import Vehicle


class VehicleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Vehicle]:
        return list(self._session.scalars(select(Vehicle).order_by(Vehicle.plate, Vehicle.id)))

    def get(self, vehicle_id: int) -> Vehicle | None:
        return self._session.get(Vehicle, vehicle_id)

    def get_by_plate(self, plate: str) -> Vehicle | None:
        return self._session.scalar(select(Vehicle).where(Vehicle.plate == plate))

    def add(self, vehicle: Vehicle) -> Vehicle:
        self._session.add(vehicle)
        self._session.commit()
        self._session.refresh(vehicle)
        return vehicle

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._session.commit()
        self._session.refresh(vehicle)
        return vehicle

    def delete(self, vehicle: Vehicle) -> None:
        self._session.delete(vehicle)
        self._session.commit()
