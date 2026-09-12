from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status

from garage_lpr.api.dependencies import CurrentUser, DatabaseSession
from garage_lpr.api.schemas.auth import (
    AdminSetupRequest,
    CurrentUserRead,
    LoginRequest,
    SetupStatusRead,
)
from garage_lpr.auth.domain import AuthenticatedPrincipal, IssuedSession
from garage_lpr.auth.service import (
    AuthenticationFailedError,
    AuthenticationService,
    LoginRateLimitedError,
    PasswordPolicyError,
    SetupAlreadyCompleteError,
)
from garage_lpr.events.domain import OperationalEvent
from garage_lpr.events.types import EventType

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(request: Request) -> AuthenticationService:
    return request.app.state.authentication_service


def _client_identity(request: Request) -> str:
    return request.client.host if request.client is not None else "local"


def _user_read(principal: AuthenticatedPrincipal) -> CurrentUserRead:
    return CurrentUserRead(
        id=principal.user_id,
        username=principal.username,
        role=principal.role,
        session_expires_at=principal.expires_at,
    )


def _set_auth_cookies(response: Response, request: Request, issued: IssuedSession) -> None:
    settings = request.app.state.settings
    max_age = max(
        1,
        int((issued.principal.expires_at - datetime.now(UTC)).total_seconds()),
    )
    response.set_cookie(
        settings.session_cookie_name,
        issued.session_token,
        max_age=max_age,
        expires=issued.principal.expires_at,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        issued.csrf_token,
        max_age=max_age,
        expires=issued.principal.expires_at,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )


def _clear_auth_cookies(response: Response, request: Request) -> None:
    settings = request.app.state.settings
    for name, httponly in (
        (settings.session_cookie_name, True),
        (settings.csrf_cookie_name, False),
    ):
        response.delete_cookie(
            name,
            path="/",
            secure=settings.secure_cookies,
            httponly=httponly,
            samesite="strict",
        )


def _publish_auth_event(
    request: Request,
    event_type: EventType,
    status_value: str,
    *,
    user_id: int | None = None,
) -> None:
    request.app.state.event_service.publish(
        OperationalEvent.create(
            event_type,
            status_value,
            metadata={"user_id": user_id, "client": _client_identity(request)},
        )
    )


@router.get("/setup-status", response_model=SetupStatusRead)
def setup_status(request: Request, session: DatabaseSession) -> SetupStatusRead:
    return SetupStatusRead(
        setup_required=_service(request).setup_required(session),
        csrf_cookie_name=request.app.state.settings.csrf_cookie_name,
    )


@router.post("/setup", response_model=CurrentUserRead, status_code=status.HTTP_201_CREATED)
def setup_admin(
    payload: AdminSetupRequest,
    response: Response,
    request: Request,
    session: DatabaseSession,
) -> CurrentUserRead:
    try:
        issued = _service(request).setup_admin(
            session,
            payload.username,
            payload.password.get_secret_value(),
        )
    except SetupAlreadyCompleteError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Setup is complete"
        ) from error
    except PasswordPolicyError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    _set_auth_cookies(response, request, issued)
    _publish_auth_event(
        request,
        EventType.ADMIN_CREATED,
        "ADMIN_CREATED",
        user_id=issued.principal.user_id,
    )
    return _user_read(issued.principal)


@router.post("/login", response_model=CurrentUserRead)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    session: DatabaseSession,
) -> CurrentUserRead:
    try:
        issued = _service(request).login(
            session,
            payload.username,
            payload.password.get_secret_value(),
            _client_identity(request),
        )
    except LoginRateLimitedError as error:
        _publish_auth_event(request, EventType.USER_LOGIN_FAILED, "RATE_LIMITED")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts; try again later",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except AuthenticationFailedError as error:
        _publish_auth_event(request, EventType.USER_LOGIN_FAILED, "INVALID_CREDENTIALS")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from error
    _set_auth_cookies(response, request, issued)
    _publish_auth_event(
        request,
        EventType.USER_LOGIN_SUCCESS,
        "AUTHENTICATED",
        user_id=issued.principal.user_id,
    )
    return _user_read(issued.principal)


@router.get("/me", response_model=CurrentUserRead)
def me(principal: CurrentUser) -> CurrentUserRead:
    return _user_read(principal)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    request: Request,
    session: DatabaseSession,
    principal: CurrentUser,
) -> None:
    settings = request.app.state.settings
    _service(request).logout(session, request.cookies.get(settings.session_cookie_name))
    _clear_auth_cookies(response, request)
    _publish_auth_event(
        request,
        EventType.USER_LOGOUT,
        "LOGGED_OUT",
        user_id=principal.user_id,
    )
