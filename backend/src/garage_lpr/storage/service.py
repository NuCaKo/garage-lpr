import logging
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any

from garage_lpr.storage.contracts import SnapshotStorage

PRUNE_INTERVAL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class SnapshotServiceSnapshot:
    enabled: bool
    healthy: bool
    detail: str
    saved: int
    failed: int
    pruned: int


class SnapshotService:
    def __init__(
        self,
        storage: SnapshotStorage,
        *,
        enabled: bool,
        retention_days: int,
    ) -> None:
        self._storage = storage
        self._lock = Lock()
        self._enabled = enabled
        self._retention_days = retention_days
        self._last_prune_monotonic: float | None = None
        self._saved = 0
        self._failed = 0
        self._pruned = 0
        self._last_error: str | None = None
        self._logger = logging.getLogger("garage_lpr.storage.snapshots")
        if enabled:
            with self._lock:
                self._prune_if_due()

    def configure(self, *, enabled: bool, retention_days: int) -> None:
        with self._lock:
            self._enabled = enabled
            self._retention_days = retention_days
            if enabled:
                self._prune_if_due()

    def capture(self, event_id: str, image: Any) -> str | None:
        with self._lock:
            if not self._enabled:
                return None
            try:
                self._prune_if_due()
                path = self._storage.save(event_id, image)
                self._saved += 1
                self._last_error = None
                return path.as_posix()
            except Exception as error:
                self._failed += 1
                self._last_error = type(error).__name__
                self._logger.error(
                    "snapshot_write_failed",
                    extra={"metadata": {"error_type": type(error).__name__}},
                )
                return None

    def snapshot(self) -> SnapshotServiceSnapshot:
        with self._lock:
            if not self._enabled:
                detail = "Event snapshots are disabled"
            elif self._last_error:
                detail = f"Last snapshot operation failed: {self._last_error}"
            else:
                detail = f"{self._saved} event snapshots saved; {self._pruned} pruned"
            return SnapshotServiceSnapshot(
                enabled=self._enabled,
                healthy=self._last_error is None,
                detail=detail,
                saved=self._saved,
                failed=self._failed,
                pruned=self._pruned,
            )

    def _prune_if_due(self) -> None:
        now = monotonic()
        if (
            self._last_prune_monotonic is not None
            and now - self._last_prune_monotonic < PRUNE_INTERVAL_SECONDS
        ):
            return
        self._pruned += self._storage.prune(self._retention_days)
        self._last_prune_monotonic = now
