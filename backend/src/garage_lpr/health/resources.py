from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic

import psutil


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    system_cpu_percent: float
    system_ram_percent: float
    system_ram_used_bytes: int
    system_ram_total_bytes: int
    process_cpu_percent: float
    process_rss_bytes: int
    process_thread_count: int
    disk_percent: float
    disk_free_bytes: int
    uptime_seconds: float


class ResourceMonitor:
    """Samples process and host scalars only when the low-frequency API is read."""

    def __init__(self, disk_path: Path) -> None:
        self._process = psutil.Process()
        self._disk_path = disk_path
        self._started_monotonic = monotonic()
        self._lock = Lock()
        self._process.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None)

    def snapshot(self) -> ResourceSnapshot:
        with self._lock:
            memory = psutil.virtual_memory()
            process_memory = self._process.memory_info()
            disk = psutil.disk_usage(str(self._disk_path))
            return ResourceSnapshot(
                system_cpu_percent=round(psutil.cpu_percent(interval=None), 2),
                system_ram_percent=round(memory.percent, 2),
                system_ram_used_bytes=memory.used,
                system_ram_total_bytes=memory.total,
                process_cpu_percent=round(self._process.cpu_percent(interval=None), 2),
                process_rss_bytes=process_memory.rss,
                process_thread_count=self._process.num_threads(),
                disk_percent=round(disk.percent, 2),
                disk_free_bytes=disk.free,
                uptime_seconds=round(monotonic() - self._started_monotonic, 1),
            )
