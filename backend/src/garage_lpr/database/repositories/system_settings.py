from typing import Any

from sqlalchemy.orm import Session

from garage_lpr.database.models import SystemSetting


class SystemSettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str) -> dict[str, Any] | None:
        setting = self._session.get(SystemSetting, key)
        return setting.value if setting is not None else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        setting = self._session.get(SystemSetting, key)
        if setting is None:
            self._session.add(SystemSetting(key=key, value=value))
        else:
            setting.value = value
            setting.version += 1
        self._session.commit()
