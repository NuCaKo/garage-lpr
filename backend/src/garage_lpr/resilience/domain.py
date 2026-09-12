from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class StabilityStatus(StrEnum):
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    TARGET_EXITED = "TARGET_EXITED"
    TARGET_UNAVAILABLE = "TARGET_UNAVAILABLE"
    INTERRUPTED = "INTERRUPTED"


@dataclass(frozen=True, slots=True)
class ProcessMeasurement:
    rss_bytes: int
    cpu_percent: float
    thread_count: int


@dataclass(frozen=True, slots=True)
class StabilityThresholds:
    max_rss_growth_bytes: int = 128 * 1024 * 1024
    max_rss_slope_bytes_per_hour: int = 4 * 1024 * 1024
    max_thread_growth: int = 2

    def __post_init__(self) -> None:
        if self.max_rss_growth_bytes < 0:
            raise ValueError("Maximum RSS growth must not be negative")
        if self.max_rss_slope_bytes_per_hour < 0:
            raise ValueError("Maximum RSS slope must not be negative")
        if self.max_thread_growth < 0:
            raise ValueError("Maximum thread growth must not be negative")


@dataclass(frozen=True, slots=True)
class StabilityReport:
    schema_version: int
    status: StabilityStatus
    target_pid: int
    started_at: datetime
    updated_at: datetime
    elapsed_seconds: float
    warmup_seconds: float
    sample_count: int
    evaluated_sample_count: int
    baseline_rss_bytes: int | None
    latest_rss_bytes: int | None
    peak_rss_bytes: int | None
    rss_growth_bytes: int | None
    rss_slope_bytes_per_hour: float | None
    average_cpu_percent: float | None
    peak_cpu_percent: float | None
    baseline_thread_count: int | None
    latest_thread_count: int | None
    peak_thread_count: int | None
    thread_growth: int | None
    thresholds: StabilityThresholds
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["started_at"] = self.started_at.isoformat()
        payload["updated_at"] = self.updated_at.isoformat()
        return payload
