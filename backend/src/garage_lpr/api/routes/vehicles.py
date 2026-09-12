from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from garage_lpr.access.vehicles import VehicleService
from garage_lpr.api.dependencies import get_database_session
from garage_lpr.api.schemas.vehicles import (
    VehicleCreate,
    VehicleRead,
    VehicleUpdate,
)
from garage_lpr.database.models import Vehicle
from garage_lpr.database.repositories.vehicles import VehicleRepository

router = APIRouter(prefix="/vehicles", tags=["vehicles"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def _service(session: Session) -> VehicleService:
    return VehicleService(VehicleRepository(session))


def _get_or_404(service: VehicleService, vehicle_id: int) -> Vehicle:
    vehicle = service.get(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


@router.get("", response_model=list[VehicleRead])
def list_vehicles(session: DatabaseSession) -> list[VehicleRead]:
    return [VehicleRead.from_vehicle(vehicle) for vehicle in _service(session).list_all()]


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, session: DatabaseSession) -> VehicleRead:
    try:
        vehicle = _service(session).create(payload.persistence_values())
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Plate already exists",
        ) from error
    return VehicleRead.from_vehicle(vehicle)


@router.put("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    session: DatabaseSession,
) -> VehicleRead:
    service = _service(session)
    vehicle = _get_or_404(service, vehicle_id)
    try:
        updated = service.update(vehicle, payload.persistence_values())
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Plate already exists",
        ) from error
    return VehicleRead.from_vehicle(updated)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, session: DatabaseSession) -> Response:
    service = _service(session)
    service.delete(_get_or_404(service, vehicle_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
