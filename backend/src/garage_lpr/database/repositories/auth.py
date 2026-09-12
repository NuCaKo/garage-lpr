from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from garage_lpr.database.models import User, UserRole, UserSession


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count(self) -> int:
        return int(self._session.scalar(select(func.count(User.id))) or 0)

    def get_by_username(self, username: str) -> User | None:
        return self._session.scalar(select(User).where(User.username == username))

    def create_admin(self, username: str, password_hash: str) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            role=UserRole.ADMIN.value,
            active=True,
        )
        self._session.add(user)
        self._session.flush()
        return user


class UserSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_user(
        self,
        user_id: int,
        token_hash: str,
        csrf_token_hash: str,
        expires_at: datetime,
    ) -> UserSession:
        self._session.execute(delete(UserSession).where(UserSession.user_id == user_id))
        auth_session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            csrf_token_hash=csrf_token_hash,
            expires_at=expires_at,
        )
        self._session.add(auth_session)
        self._session.flush()
        return auth_session

    def get_with_user(self, token_hash: str) -> tuple[UserSession, User] | None:
        row = self._session.execute(
            select(UserSession, User)
            .join(User, User.id == UserSession.user_id)
            .where(UserSession.token_hash == token_hash)
        ).one_or_none()
        return (row[0], row[1]) if row is not None else None

    def delete_by_token_hash(self, token_hash: str) -> None:
        self._session.execute(delete(UserSession).where(UserSession.token_hash == token_hash))

    def delete_expired(self, cutoff: datetime) -> None:
        self._session.execute(delete(UserSession).where(UserSession.expires_at <= cutoff))
