from datetime import UTC, datetime, timedelta
from os import utime
from pathlib import Path

import numpy as np

from garage_lpr.storage.local import LocalSnapshotStorage
from garage_lpr.storage.service import SnapshotService


def test_snapshot_service_writes_only_when_enabled_and_prunes_old_files(tmp_path: Path) -> None:
    storage = LocalSnapshotStorage(tmp_path, jpeg_quality=60)
    image = np.zeros((20, 40, 3), dtype=np.uint8)
    service = SnapshotService(storage, enabled=False, retention_days=30)

    assert service.capture("disabled1", image) is None
    assert list(tmp_path.rglob("*.jpg")) == []

    service.configure(enabled=True, retention_days=30)
    relative_path = service.capture("enabled1", image)

    assert relative_path is not None
    target = tmp_path / relative_path
    assert target.exists()
    old = (datetime.now(UTC) - timedelta(days=31)).timestamp()
    utime(target, (old, old))
    assert storage.prune(30) == 1
    assert not target.exists()
