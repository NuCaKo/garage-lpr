from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from garage_lpr.api.dependencies import get_database_session
from garage_lpr.api.schemas.gates import (
    GateConnectionRead,
    GateControllerCreate,
    GateControllerRead,
    GateControllerUpdate,
)
from garage_lpr.database.models import GateControllerConfig
from garage_lpr.database.repositories.gates import GateControllerRepository
from garage_lpr.gate.service import GateControllerService

router = APIRouter(prefix="/gate-controllers", tags=["gate-controllers"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def _service(session: Session) -> GateControllerService:
    return GateControllerService(GateControllerRepository(session))


def _get_or_404(service: GateControllerService, gate_id: int) -> GateControllerConfig:
    gate = service.get(gate_id)
    if gate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gate controller not found"
        )
    return gate


def _read(request: Request, gate: GateControllerConfig) -> GateControllerRead:
    runtime = request.app.state.gate_manager.snapshot(gate.id)
    return GateControllerRead.from_gate(gate, runtime)


@router.get("", response_model=list[GateControllerRead])
def list_gate_controllers(request: Request, session: DatabaseSession) -> list[GateControllerRead]:
    return [_read(request, gate) for gate in _service(session).list_all()]


@router.post("", response_model=GateControllerRead, status_code=status.HTTP_201_CREATED)
def create_gate_controller(
    payload: GateControllerCreate, request: Request, session: DatabaseSession
) -> GateControllerRead:
    service = _service(session)
    try:
        gate = service.create(payload.model_dump(mode="json"))
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Gate controller name already exists",
        ) from error
    if gate.active:
        request.app.state.gate_manager.apply(service.runtime_configuration(gate))
    return _read(request, gate)


@router.put("/{gate_id}", response_model=GateControllerRead)
def update_gate_controller(
    gate_id: int,
    payload: GateControllerUpdate,
    request: Request,
    session: DatabaseSession,
) -> GateControllerRead:
    service = _service(session)
    gate = _get_or_404(service, gate_id)
    try:
        gate = service.update(gate, payload.model_dump(mode="json"))
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Gate controller name already exists",
        ) from error
    if gate.active:
        request.app.state.gate_manager.apply(service.runtime_configuration(gate))
    else:
        request.app.state.gate_manager.remove(gate.id)
    return _read(request, gate)


@router.delete("/{gate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gate_controller(gate_id: int, request: Request, session: DatabaseSession) -> Response:
    service = _service(session)
    gate = _get_or_404(service, gate_id)
    request.app.state.gate_manager.remove(gate.id)
    service.delete(gate)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{gate_id}/test-connection", response_model=GateConnectionRead)
def test_gate_connection(
    gate_id: int, request: Request, session: DatabaseSession
) -> GateConnectionRead:
    service = _service(session)
    gate = _get_or_404(service, gate_id)
    if not gate.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Gate controller is not active",
        )
    runtime = request.app.state.gate_manager.snapshot(gate.id)
    return GateConnectionRead(
        connected=runtime.healthy,
        state=runtime.state,
        detail=runtime.detail,
    )
