from sqlalchemy.orm import Session

from garage_lpr.config.settings import RuntimeSettings
from garage_lpr.database.repositories.system_settings import SystemSettingsRepository


class ConfigurationService:
    RUNTIME_KEY = "runtime"

    def __init__(self, session: Session) -> None:
        self._repository = SystemSettingsRepository(session)

    def get_runtime_settings(self) -> RuntimeSettings:
        stored = self._repository.get(self.RUNTIME_KEY)
        return RuntimeSettings.model_validate(stored) if stored is not None else RuntimeSettings()

    def update_runtime_settings(self, settings: RuntimeSettings) -> RuntimeSettings:
        self._repository.put(self.RUNTIME_KEY, settings.model_dump(mode="json"))
        return settings
