import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretCipher:
    def __init__(self, key_path: Path) -> None:
        self._fernet = Fernet(self._load_or_create_key(key_path))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes | None) -> str | None:
        if ciphertext is None:
            return None
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken as error:
            raise ValueError("Stored camera credential cannot be decrypted") from error

    @staticmethod
    def _load_or_create_key(key_path: Path) -> bytes:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return key_path.read_bytes()
        except FileNotFoundError:
            key = Fernet.generate_key()
            try:
                descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                return key_path.read_bytes()
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(key)
            return key
