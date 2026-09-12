from datetime import UTC, datetime
from typing import Protocol

import psutil

from garage_lpr.resilience.domain import (
    ProcessMeasurement,
    StabilityReport,
    StabilityStatus,
    StabilityThresholds,
)

SECONDS_PER_HOUR = 3600.0


class ProcessProbe(Protocol):
    def sample(self) -> ProcessMeasurement: ...


class PsutilProcessProbe:
    def __init__(self, process_id: int) -> None:
        self._process = psutil.Process(process_id)
        self._process.cpu_percent(interval=None)

    def sample(self) -> ProcessMeasurement:
        if not self._process.is_running():
            raise psutil.NoSuchProcess(self._process.pid)
        return ProcessMeasurement(
            rss_bytes=self._process.memory_info().rss,
            cpu_percent=round(self._process.cpu_percent(interval=None), 2),
            thread_count=self._process.num_threads(),
        )


class _ScalarTrend:
    """Constant-memory online mean and linear regression accumulator."""

    def __init__(self) -> None:
        self.count = 0
        self.sum_x = 0.0
        self.sum_y = 0.0
        self.sum_xy = 0.0
        self.sum_x_squared = 0.0

    def add(self, x_value: float, y_value: float) -> None:
        self.count += 1
        self.sum_x += x_value
        self.sum_y += y_value
        self.sum_xy += x_value * y_value
        self.sum_x_squared += x_value * x_value

    @property
    def mean(self) -> float | None:
        return self.sum_y / self.count if self.count else None

    @property
    def slope(self) -> float | None:
        if self.count < 2:
            return None
        denominator = self.count * self.sum_x_squared - self.sum_x * self.sum_x
        if denominator == 0:
            return 0.0
        return (self.count * self.sum_xy - self.sum_x * self.sum_y) / denominator


class ProcessStabilityMonitor:
    """Evaluates a process using scalar aggregates; no sample history is retained."""

    def __init__(
        self,
        target_pid: int,
        thresholds: StabilityThresholds,
        warmup_seconds: float,
        *,
        probe: ProcessProbe | None = None,
        started_at: datetime | None = None,
    ) -> None:
        if target_pid <= 0:
            raise ValueError("Target PID must be positive")
        if warmup_seconds < 0:
            raise ValueError("Warmup duration must not be negative")
        self._target_pid = target_pid
        self._thresholds = thresholds
        self._warmup_seconds = warmup_seconds
        self._probe = probe or PsutilProcessProbe(target_pid)
        self._started_at = started_at or datetime.now(UTC)
        self._sample_count = 0
        self._baseline: ProcessMeasurement | None = None
        self._latest: ProcessMeasurement | None = None
        self._peak_rss_bytes: int | None = None
        self._peak_cpu_percent: float | None = None
        self._peak_thread_count: int | None = None
        self._rss_trend = _ScalarTrend()
        self._cpu_trend = _ScalarTrend()

    def sample(self, elapsed_seconds: float) -> ProcessMeasurement:
        if elapsed_seconds < 0:
            raise ValueError("Elapsed duration must not be negative")
        measurement = self._probe.sample()
        self._sample_count += 1
        self._latest = measurement
        if elapsed_seconds < self._warmup_seconds:
            return measurement
        if self._baseline is None:
            self._baseline = measurement
        self._peak_rss_bytes = max(self._peak_rss_bytes or 0, measurement.rss_bytes)
        self._peak_cpu_percent = max(self._peak_cpu_percent or 0.0, measurement.cpu_percent)
        self._peak_thread_count = max(self._peak_thread_count or 0, measurement.thread_count)
        evaluation_elapsed = elapsed_seconds - self._warmup_seconds
        self._rss_trend.add(evaluation_elapsed, float(measurement.rss_bytes))
        self._cpu_trend.add(evaluation_elapsed, measurement.cpu_percent)
        return measurement

    def report(
        self,
        elapsed_seconds: float,
        status: StabilityStatus = StabilityStatus.RUNNING,
        *,
        reason: str | None = None,
    ) -> StabilityReport:
        reasons = list(self._threshold_failures()) if self._baseline is not None else []
        if reason:
            reasons.append(reason)
        if status is StabilityStatus.PASSED and reasons:
            status = StabilityStatus.FAILED
        baseline = self._baseline
        latest = self._latest
        rss_slope = self._rss_trend.slope
        return StabilityReport(
            schema_version=1,
            status=status,
            target_pid=self._target_pid,
            started_at=self._started_at,
            updated_at=datetime.now(UTC),
            elapsed_seconds=round(elapsed_seconds, 3),
            warmup_seconds=self._warmup_seconds,
            sample_count=self._sample_count,
            evaluated_sample_count=self._rss_trend.count,
            baseline_rss_bytes=baseline.rss_bytes if baseline else None,
            latest_rss_bytes=latest.rss_bytes if latest else None,
            peak_rss_bytes=self._peak_rss_bytes,
            rss_growth_bytes=(
                latest.rss_bytes - baseline.rss_bytes if baseline and latest else None
            ),
            rss_slope_bytes_per_hour=(
                round(rss_slope * SECONDS_PER_HOUR, 2) if rss_slope is not None else None
            ),
            average_cpu_percent=(
                round(self._cpu_trend.mean, 2) if self._cpu_trend.mean is not None else None
            ),
            peak_cpu_percent=self._peak_cpu_percent,
            baseline_thread_count=baseline.thread_count if baseline else None,
            latest_thread_count=latest.thread_count if latest else None,
            peak_thread_count=self._peak_thread_count,
            thread_growth=(
                self._peak_thread_count - baseline.thread_count
                if baseline and self._peak_thread_count is not None
                else None
            ),
            thresholds=self._thresholds,
            reasons=tuple(reasons),
        )

    def _threshold_failures(self) -> tuple[str, ...]:
        baseline = self._baseline
        latest = self._latest
        if baseline is None or latest is None:
            return ("No samples were collected after warmup",)
        failures: list[str] = []
        rss_growth = latest.rss_bytes - baseline.rss_bytes
        if rss_growth > self._thresholds.max_rss_growth_bytes:
            failures.append("RSS growth exceeded the configured limit")
        rss_slope = self._rss_trend.slope
        if (
            rss_slope is not None
            and rss_slope * SECONDS_PER_HOUR
            > self._thresholds.max_rss_slope_bytes_per_hour
        ):
            failures.append("RSS growth slope exceeded the configured hourly limit")
        peak_threads = self._peak_thread_count or baseline.thread_count
        if peak_threads - baseline.thread_count > self._thresholds.max_thread_growth:
            failures.append("Thread growth exceeded the configured limit")
        return tuple(failures)
