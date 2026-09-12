from pathlib import Path
from typing import Any, Protocol


class SnapshotStorage(Protocol):
    def save(self, event_id: str, image: Any) -> Path: ...

    def prune(self, retention_days: int) -> int: ...
