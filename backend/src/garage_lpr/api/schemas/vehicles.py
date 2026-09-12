from datetime import date, datetime, time
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from garage_lpr.database.models import Vehicle
from garage_lpr.ocr.normalizer import TurkishPlateNormalizer


class VehicleWrite(BaseModel):
    plate: str = Field(min_length=5, max_length=16)
    owner: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    active: bool = True
    valid_from: date | None = None
    valid_until: date | None = None
    allowed_days: list[int] = Field(default_factory=lambda: list(range(7)), max_length=7)
    allowed_start_time: time | None = None
    allowed_end_time: time | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        result = TurkishPlateNormalizer().normalize(value)
        if not result.valid_format:
            raise ValueError("A valid Turkish plate is required")
        return result.text

    @field_validator("owner")
    @classmethod
    def normalize_owner(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Owner cannot be blank")
        return normalized

    @field_validator("description", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        normalized = value.strip() if value is not None else None
        return normalized or None

    @field_validator("allowed_days")
    @classmethod
    def validate_allowed_days(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("Allowed days must use Monday=0 through Sunday=6")
        if len(set(value)) != len(value):
            raise ValueError("Allowed days cannot contain duplicates")
        return sorted(value)

    @model_validator(mode="after")
    def validate_intervals(self) -> Self:
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError("valid_from cannot be later than valid_until")
        if (self.allowed_start_time is None) != (self.allowed_end_time is None):
            raise ValueError("Allowed start and end time must be set together")
        return self

    def persistence_values(self) -> dict[str, object]:
        return self.model_dump(mode="python")


class VehicleCreate(VehicleWrite):
    pass


class VehicleUpdate(VehicleWrite):
    pass


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plate: str
    owner: str
    description: str | None
    active: bool
    valid_from: date | None
    valid_until: date | None
    allowed_days: list[int]
    allowed_start_time: time | None
    allowed_end_time: time | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_vehicle(cls, vehicle: Vehicle) -> "VehicleRead":
        return cls.model_validate(vehicle)
