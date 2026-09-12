from garage_lpr.database.models import Vehicle
from garage_lpr.database.repositories.vehicles import VehicleRepository
from garage_lpr.ocr.normalizer import TurkishPlateNormalizer


class InvalidVehiclePlateError(ValueError):
    pass


class VehicleService:
    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository
        self._normalizer = TurkishPlateNormalizer()

    def list_all(self) -> list[Vehicle]:
        return self._repository.list_all()

    def get(self, vehicle_id: int) -> Vehicle | None:
        return self._repository.get(vehicle_id)

    def create(self, values: dict[str, object]) -> Vehicle:
        values["plate"] = self._canonical_plate(str(values["plate"]))
        return self._repository.add(Vehicle(**values))

    def update(self, vehicle: Vehicle, values: dict[str, object]) -> Vehicle:
        values["plate"] = self._canonical_plate(str(values["plate"]))
        for name, value in values.items():
            setattr(vehicle, name, value)
        return self._repository.save(vehicle)

    def delete(self, vehicle: Vehicle) -> None:
        self._repository.delete(vehicle)

    def _canonical_plate(self, value: str) -> str:
        normalized = self._normalizer.normalize(value)
        if not normalized.valid_format:
            raise InvalidVehiclePlateError("A valid Turkish plate is required")
        return normalized.text
