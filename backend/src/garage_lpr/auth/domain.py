from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user_id: int
    username: str
    role: str
    session_id: int
    csrf_token_hash: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedSession:
    principal: AuthenticatedPrincipal
    session_token: str
    csrf_token: str
