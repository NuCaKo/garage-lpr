from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import compare_digest, token_urlsafe
from threading import Lock
from typing import NoReturn

from sqlalchemy.orm import Session

from garage_lpr.auth.domain import AuthenticatedPrincipal, IssuedSession
from garage_lpr.auth.limiter import LoginAttemptLimiter
from garage_lpr.auth.passwords import Argon2PasswordService
from garage_lpr.database.repositories.auth import UserRepository, UserSessionRepository


class AuthenticationFailedError(Exception):
    pass


class SetupAlreadyCompleteError(Exception):
    pass


class PasswordPolicyError(Exception):
    pass


class LoginRateLimitedError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Login temporarily locked")
        self.retry_after_seconds = retry_after_seconds


class CsrfValidationError(Exception):
    pass


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AuthenticationService:
    def __init__(
        self,
        passwords: Argon2PasswordService,
        limiter: LoginAttemptLimiter,
        session_ttl_hours: int,
    ) -> None:
        self._passwords = passwords
        self._limiter = limiter
        self._session_ttl = timedelta(hours=session_ttl_hours)
        self._setup_lock = Lock()

    def setup_required(self, session: Session) -> bool:
        return UserRepository(session).count() == 0

    def setup_admin(self, session: Session, username: str, password: str) -> IssuedSession:
        self._validate_password(username, password)
        with self._setup_lock:
            users = UserRepository(session)
            if users.count() != 0:
                raise SetupAlreadyCompleteError
            user = users.create_admin(username, self._passwords.hash(password))
            issued = self._issue(session, user.id, user.username, user.role)
            session.commit()
            return issued

    def login(
        self,
        session: Session,
        username: str,
        password: str,
        client_identity: str,
    ) -> IssuedSession:
        limiter_key = f"{client_identity}:{username}"
        retry_after = self._limiter.retry_after(limiter_key)
        if retry_after:
            raise LoginRateLimitedError(retry_after)

        users = UserRepository(session)
        user = users.get_by_username(username)
        if user is None:
            self._passwords.verify_dummy(password)
            self._record_login_failure(limiter_key)
        if user is None:
            raise AuthenticationFailedError
        password_valid = self._passwords.verify(user.password_hash, password)
        if not user.active or not password_valid:
            self._record_login_failure(limiter_key)

        if self._passwords.needs_rehash(user.password_hash):
            user.password_hash = self._passwords.hash(password)
        issued = self._issue(session, user.id, user.username, user.role)
        session.commit()
        self._limiter.reset(limiter_key)
        return issued

    def authenticate(self, session: Session, session_token: str | None) -> AuthenticatedPrincipal:
        if not session_token:
            raise AuthenticationFailedError
        token_hash = _digest(session_token)
        pair = UserSessionRepository(session).get_with_user(token_hash)
        if pair is None:
            raise AuthenticationFailedError
        auth_session, user = pair
        if _as_utc(auth_session.expires_at) <= datetime.now(UTC) or not user.active:
            UserSessionRepository(session).delete_by_token_hash(token_hash)
            session.commit()
            raise AuthenticationFailedError
        return AuthenticatedPrincipal(
            user_id=user.id,
            username=user.username,
            role=user.role,
            session_id=auth_session.id,
            csrf_token_hash=auth_session.csrf_token_hash,
            expires_at=_as_utc(auth_session.expires_at),
        )

    def verify_csrf(
        self,
        principal: AuthenticatedPrincipal,
        header_token: str | None,
        cookie_token: str | None,
    ) -> None:
        if not header_token or not cookie_token:
            raise CsrfValidationError
        if not compare_digest(header_token, cookie_token):
            raise CsrfValidationError
        if not compare_digest(_digest(header_token), principal.csrf_token_hash):
            raise CsrfValidationError

    def logout(self, session: Session, session_token: str | None) -> None:
        if session_token:
            UserSessionRepository(session).delete_by_token_hash(_digest(session_token))
            session.commit()

    def _issue(self, session: Session, user_id: int, username: str, role: str) -> IssuedSession:
        now = datetime.now(UTC)
        expires_at = now + self._session_ttl
        session_token = token_urlsafe(32)
        csrf_token = token_urlsafe(32)
        repository = UserSessionRepository(session)
        repository.delete_expired(now)
        auth_session = repository.replace_for_user(
            user_id,
            _digest(session_token),
            _digest(csrf_token),
            expires_at,
        )
        return IssuedSession(
            principal=AuthenticatedPrincipal(
                user_id=user_id,
                username=username,
                role=role,
                session_id=auth_session.id,
                csrf_token_hash=auth_session.csrf_token_hash,
                expires_at=expires_at,
            ),
            session_token=session_token,
            csrf_token=csrf_token,
        )

    def _record_login_failure(self, limiter_key: str) -> NoReturn:
        retry_after = self._limiter.record_failure(limiter_key)
        if retry_after:
            raise LoginRateLimitedError(retry_after)
        raise AuthenticationFailedError

    @staticmethod
    def _validate_password(username: str, password: str) -> None:
        if len(password) < 12:
            raise PasswordPolicyError("Password must contain at least 12 characters")
        if len(username) >= 4 and username.casefold() in password.casefold():
            raise PasswordPolicyError("Password must not contain the username")
