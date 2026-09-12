from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from garage_lpr.api.dependencies import get_database_session
from garage_lpr.config.service import ConfigurationService
from garage_lpr.config.settings import RuntimeSettings

router = APIRouter(prefix="/system-settings", tags=["system-settings"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("", response_model=RuntimeSettings)
def get_runtime_settings(session: DatabaseSession) -> RuntimeSettings:
    return ConfigurationService(session).get_runtime_settings()


@router.put("", response_model=RuntimeSettings, status_code=status.HTTP_200_OK)
def update_runtime_settings(
    payload: RuntimeSettings, request: Request, session: DatabaseSession
) -> RuntimeSettings:
    updated = ConfigurationService(session).update_runtime_settings(payload)
    request.app.state.event_service.configure_retention(updated.event_retention_days)
    request.app.state.snapshot_service.configure(
        enabled=updated.snapshot_enabled,
        retention_days=updated.snapshot_retention_days,
    )
    request.app.state.inference_manager.configure(updated)
    return updated
