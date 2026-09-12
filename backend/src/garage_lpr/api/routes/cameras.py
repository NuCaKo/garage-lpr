from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from garage_lpr.api.dependencies import get_database_session
from garage_lpr.api.schemas.cameras import (
    CameraConnectionRead,
    CameraCreate,
    CameraRead,
    CameraUpdate,
)
from garage_lpr.camera.service import CameraLimitError, CameraService
from garage_lpr.database.models import Camera
from garage_lpr.database.repositories.cameras import CameraRepository

router = APIRouter(prefix="/cameras", tags=["cameras"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def _service(request: Request, session: Session) -> CameraService:
    return CameraService(
        CameraRepository(session),
        request.app.state.secret_cipher,
        request.app.state.settings.max_active_cameras,
    )


def _get_or_404(service: CameraService, camera_id: int) -> Camera:
    camera = service.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


def _read(request: Request, camera: Camera) -> CameraRead:
    runtime = request.app.state.camera_manager.snapshot(camera.id)
    return CameraRead.from_camera(camera, runtime)


@router.get("", response_model=list[CameraRead])
def list_cameras(request: Request, session: DatabaseSession) -> list[CameraRead]:
    return [_read(request, camera) for camera in _service(request, session).list_all()]


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate, request: Request, session: DatabaseSession) -> CameraRead:
    service = _service(request, session)
    try:
        camera = service.create(
            payload.persistence_values(),
            payload.password.get_secret_value() if payload.password else None,
        )
    except CameraLimitError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Camera name already exists"
        ) from error
    if camera.active:
        request.app.state.camera_manager.apply(service.runtime_configuration(camera))
    request.app.state.inference_manager.apply_camera(service.inference_configuration(camera))
    return _read(request, camera)


@router.put("/{camera_id}", response_model=CameraRead)
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    request: Request,
    session: DatabaseSession,
) -> CameraRead:
    service = _service(request, session)
    camera = _get_or_404(service, camera_id)
    try:
        camera = service.update(
            camera,
            payload.persistence_values(),
            payload.password.get_secret_value() if payload.password else None,
            payload.clear_password,
        )
    except CameraLimitError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Camera name already exists"
        ) from error
    request.app.state.preview_encoder.evict(camera_id)
    if camera.active:
        request.app.state.camera_manager.apply(service.runtime_configuration(camera))
    else:
        request.app.state.camera_manager.stop(camera_id)
    request.app.state.inference_manager.apply_camera(service.inference_configuration(camera))
    return _read(request, camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, request: Request, session: DatabaseSession) -> Response:
    service = _service(request, session)
    camera = _get_or_404(service, camera_id)
    request.app.state.camera_manager.stop(camera_id)
    request.app.state.preview_encoder.evict(camera_id)
    request.app.state.inference_manager.remove_camera(camera_id)
    service.delete(camera)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{camera_id}/test-connection", response_model=CameraConnectionRead)
def test_camera_connection(
    camera_id: int, request: Request, session: DatabaseSession
) -> CameraConnectionRead:
    service = _service(request, session)
    camera = _get_or_404(service, camera_id)
    result = request.app.state.camera_connection_tester.test(service.runtime_configuration(camera))
    return CameraConnectionRead.from_result(result)


@router.get("/{camera_id}/preview.jpg", responses={200: {"content": {"image/jpeg": {}}}})
def camera_preview(camera_id: int, request: Request, session: DatabaseSession) -> Response:
    service = _service(request, session)
    camera = _get_or_404(service, camera_id)
    if not camera.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Camera is not active")
    frame = request.app.state.camera_manager.latest_frame(camera_id)
    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preview frame is not available yet",
        )
    payload = request.app.state.preview_encoder.encode(camera_id, frame)
    return Response(
        content=payload,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, max-age=0"},
    )
