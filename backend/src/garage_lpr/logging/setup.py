import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from garage_lpr.config.settings import BootstrapSettings

_SENSITIVE_KEYS = {"authorization", "credentials", "password", "secret", "token"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in _SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        metadata = getattr(record, "metadata", None)
        if metadata is not None:
            payload["metadata"] = _redact(metadata)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(settings: BootstrapSettings) -> None:
    log_directory = Path(settings.log_directory)
    log_directory.mkdir(parents=True, exist_ok=True)
    formatter = JsonFormatter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    rotating_file = RotatingFileHandler(
        log_directory / "garage-lpr.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    rotating_file.setFormatter(formatter)

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    root_logger.setLevel(settings.log_level)
    root_logger.addHandler(console)
    root_logger.addHandler(rotating_file)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
