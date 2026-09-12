from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from garage_lpr.access.rules import (
    AccessRuleConflictError,
    AccessRuleReferenceError,
    AccessRuleService,
)
from garage_lpr.api.dependencies import get_database_session
from garage_lpr.api.schemas.access_rules import (
    AccessRuleCreate,
    AccessRuleRead,
    AccessRuleUpdate,
)
from garage_lpr.database.models import AccessRule
from garage_lpr.database.repositories.access_rules import AccessRuleRepository
from garage_lpr.database.repositories.cameras import CameraRepository
from garage_lpr.database.repositories.gates import GateControllerRepository
from garage_lpr.database.repositories.vehicles import VehicleRepository

router = APIRouter(prefix="/access-rules", tags=["access-rules"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def _service(session: Session) -> AccessRuleService:
    return AccessRuleService(
        AccessRuleRepository(session),
        VehicleRepository(session),
        CameraRepository(session),
        GateControllerRepository(session),
    )


def _get_or_404(service: AccessRuleService, rule_id: int) -> AccessRule:
    rule = service.get(rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access rule not found")
    return rule


def _write_error(error: ValueError) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT
        if isinstance(error, AccessRuleConflictError)
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(status_code=code, detail=str(error))


@router.get("", response_model=list[AccessRuleRead])
def list_access_rules(session: DatabaseSession) -> list[AccessRuleRead]:
    return [AccessRuleRead.from_rule(rule) for rule in _service(session).list_all()]


@router.post("", response_model=AccessRuleRead, status_code=status.HTTP_201_CREATED)
def create_access_rule(payload: AccessRuleCreate, session: DatabaseSession) -> AccessRuleRead:
    try:
        rule = _service(session).create(payload.model_dump(mode="json"))
    except (AccessRuleConflictError, AccessRuleReferenceError) as error:
        raise _write_error(error) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equivalent access rule already exists",
        ) from error
    return AccessRuleRead.from_rule(rule)


@router.put("/{rule_id}", response_model=AccessRuleRead)
def update_access_rule(
    rule_id: int, payload: AccessRuleUpdate, session: DatabaseSession
) -> AccessRuleRead:
    service = _service(session)
    rule = _get_or_404(service, rule_id)
    try:
        rule = service.update(rule, payload.model_dump(mode="json"))
    except (AccessRuleConflictError, AccessRuleReferenceError) as error:
        raise _write_error(error) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equivalent access rule already exists",
        ) from error
    return AccessRuleRead.from_rule(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_access_rule(rule_id: int, session: DatabaseSession) -> Response:
    service = _service(session)
    rule = _get_or_404(service, rule_id)
    service.delete(rule)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
