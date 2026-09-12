from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from garage_lpr.database.models import GateControllerConfig
from garage_lpr.gate.domain import GateRuntimeSnapshot


class GateControllerWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    controller_type: Literal["MOCK"] = "MOCK"
    active: bool = False
    pulse_ms: int = Field(default=500, ge=50, le=5000)
    configuration: dict[str, object] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Gate controller name must not be blank")
        return normalized

    @field_validator("configuration")
    @classmethod
    def mock_configuration_is_empty(cls, value: dict[str, object]) -> dict[str, object]:
        if value:
            raise ValueError("Mock gate controller does not accept configuration values")
        return value


class GateControllerCreate(GateControllerWrite):
    pass


class GateControllerUpdate(GateControllerWrite):
    pass


class GateControllerRead(BaseModel):
    id: int
    name: str
    controller_type: str
    active: bool
    pulse_ms: int
    configuration: dict[str, object]
    runtime_state: str
    healthy: bool
    runtime_detail: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_gate(
        cls, gate: GateControllerConfig, runtime: GateRuntimeSnapshot
    ) -> "GateControllerRead":
        return cls(
            id=gate.id,
            name=gate.name,
            controller_type=gate.controller_type,
            active=gate.active,
            pulse_ms=gate.pulse_ms,
            configuration=dict(gate.configuration or {}),
            runtime_state=runtime.state,
            healthy=runtime.healthy,
            runtime_detail=runtime.detail,
            created_at=gate.created_at,
            updated_at=gate.updated_at,
        )


class GateConnectionRead(BaseModel):
    connected: bool
    state: str
    detail: str
