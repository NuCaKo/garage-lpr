from datetime import datetime

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"


class SetupStatusRead(BaseModel):
    setup_required: bool
    csrf_cookie_name: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=USERNAME_PATTERN)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class AdminSetupRequest(LoginRequest):
    password: SecretStr = Field(min_length=12, max_length=128)
    password_confirmation: SecretStr = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "AdminSetupRequest":
        if self.password.get_secret_value() != self.password_confirmation.get_secret_value():
            raise ValueError("Passwords do not match")
        return self


class CurrentUserRead(BaseModel):
    id: int
    username: str
    role: str
    session_expires_at: datetime
