from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any


class LocalSnapshotStorage:
    """Writes event-only JPEG snapshots and prunes them by file age."""

    def __init__(self, root: Path, jpeg_quality: int = 75) -> None:
        import cv2

        self._root = root
        self._quality = jpeg_quality
        self._cv2 = cv2
        self._lock = Lock()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def save(self, event_id: str, image: Any) -> Path:
        if not event_id.isalnum():
            raise ValueError("Snapshot event id must be alphanumeric")
        captured_at = datetime.now(UTC)
        target_directory = self._root / captured_at.strftime("%Y/%m/%d")
        target_directory.mkdir(parents=True, exist_ok=True)
        target = target_directory / f"{event_id}.jpg"
        with self._lock:
            success, encoded = self._cv2.imencode(
                ".jpg", image, [self._cv2.IMWRITE_JPEG_QUALITY, self._quality]
            )
            if not success:
                raise ValueError("Snapshot image could not be encoded")
            temporary = target.with_suffix(".tmp")
            temporary.write_bytes(encoded.tobytes())
            temporary.replace(target)
        return target.relative_to(self._root)

    def prune(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        removed = 0
        with self._lock:
            for snapshot in self._root.rglob("*.jpg"):
                modified_at = datetime.fromtimestamp(snapshot.stat().st_mtime, UTC)
                if modified_at < cutoff:
                    snapshot.unlink()
                    removed += 1
        return removed
