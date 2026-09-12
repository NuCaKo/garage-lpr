from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from garage_lpr.database.models import AccessRule


class AccessRuleWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    vehicle_id: int = Field(gt=0)
    camera_id: int | None = Field(default=None, gt=0)
    gate_controller_id: int = Field(gt=0)
    active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Access rule name must not be blank")
        return normalized


class AccessRuleCreate(AccessRuleWrite):
    pass


class AccessRuleUpdate(AccessRuleWrite):
    pass


class AccessRuleRead(BaseModel):
    id: int
    name: str
    vehicle_id: int
    camera_id: int | None
    gate_controller_id: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_rule(cls, rule: AccessRule) -> "AccessRuleRead":
        return cls.model_validate(rule, from_attributes=True)
