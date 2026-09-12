from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from argon2.low_level import Type


class Argon2PasswordService:
    """Argon2id password hashing with a deliberately memory-hard login cost."""

    def __init__(self, *, testing: bool = False) -> None:
        self._hasher = PasswordHasher(
            time_cost=1 if testing else 3,
            memory_cost=8_192 if testing else 65_536,
            parallelism=1 if testing else 2,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self._dummy_hash = self.hash("garage-lpr-dummy-password-value")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError):
            return False

    def verify_dummy(self, password: str) -> None:
        self.verify(self._dummy_hash, password)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)
