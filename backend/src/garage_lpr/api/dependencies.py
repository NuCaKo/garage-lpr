from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from garage_lpr.auth.domain import AuthenticatedPrincipal
from garage_lpr.auth.service import (
    AuthenticationFailedError,
    AuthenticationService,
    CsrfValidationError,
)


def get_database_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DatabaseSession = Annotated[Session, Depends(get_database_session)]


def require_current_user(
    request: Request,
    session: DatabaseSession,
) -> AuthenticatedPrincipal:
    settings = request.app.state.settings
    service: AuthenticationService = request.app.state.authentication_service
    try:
        principal = service.authenticate(
            session,
            request.cookies.get(settings.session_cookie_name),
        )
    except AuthenticationFailedError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Cookie"},
        ) from error

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        try:
            service.verify_csrf(
                principal,
                request.headers.get("X-CSRF-Token"),
                request.cookies.get(settings.csrf_cookie_name),
            )
        except CsrfValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed",
            ) from error
    return principal


CurrentUser = Annotated[AuthenticatedPrincipal, Depends(require_current_user)]


def require_admin(principal: CurrentUser) -> AuthenticatedPrincipal:
    if principal.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return principal
