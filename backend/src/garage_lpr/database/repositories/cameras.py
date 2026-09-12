from sqlalchemy import func, select
from sqlalchemy.orm import Session

from garage_lpr.database.models import Camera


class CameraRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Camera]:
        statement = select(Camera).order_by(Camera.name, Camera.id)
        return list(self._session.scalars(statement))

    def get(self, camera_id: int) -> Camera | None:
        return self._session.get(Camera, camera_id)

    def add(self, camera: Camera) -> Camera:
        self._session.add(camera)
        self._session.commit()
        self._session.refresh(camera)
        return camera

    def save(self, camera: Camera) -> Camera:
        self._session.commit()
        self._session.refresh(camera)
        return camera

    def delete(self, camera: Camera) -> None:
        self._session.delete(camera)
        self._session.commit()

    def count_active(self, excluding_id: int | None = None) -> int:
        statement = select(func.count(Camera.id)).where(Camera.active.is_(True))
        if excluding_id is not None:
            statement = statement.where(Camera.id != excluding_id)
        return int(self._session.scalar(statement) or 0)
