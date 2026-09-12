import argparse
import json
import signal
from collections.abc import Sequence
from pathlib import Path
from threading import Event
from time import monotonic

import psutil

from garage_lpr.config.settings import runtime_root
from garage_lpr.resilience.domain import StabilityStatus, StabilityThresholds
from garage_lpr.resilience.monitor import ProcessStabilityMonitor
from garage_lpr.resilience.reporting import AtomicReportWriter

DEFAULT_DURATION_HOURS = 72.0
DEFAULT_INTERVAL_SECONDS = 60.0
DEFAULT_WARMUP_MINUTES = 10.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Constant-memory process stability monitor for Garage LPR",
    )
    parser.add_argument("--pid", type=int, required=True, help="Garage LPR process ID")
    duration = parser.add_mutually_exclusive_group()
    duration.add_argument("--duration-hours", type=float, default=DEFAULT_DURATION_HOURS)
    duration.add_argument("--duration-seconds", type=float)
    parser.add_argument("--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--warmup-minutes", type=float, default=DEFAULT_WARMUP_MINUTES)
    parser.add_argument(
        "--report",
        type=Path,
        default=runtime_root() / "runtime/soak/latest.json",
    )
    parser.add_argument("--max-rss-growth-mb", type=float, default=128.0)
    parser.add_argument("--max-rss-slope-mb-per-hour", type=float, default=4.0)
    parser.add_argument("--max-thread-growth", type=int, default=2)
    return parser


def _positive(parser: argparse.ArgumentParser, name: str, value: float) -> float:
    if value <= 0:
        parser.error(f"{name} must be greater than zero")
    return value


def run(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    duration_seconds = (
        _positive(parser, "duration-seconds", args.duration_seconds)
        if args.duration_seconds is not None
        else _positive(parser, "duration-hours", args.duration_hours) * 3600.0
    )
    interval_seconds = _positive(parser, "interval-seconds", args.interval_seconds)
    if args.warmup_minutes < 0:
        parser.error("warmup-minutes must not be negative")
    if args.max_rss_growth_mb < 0 or args.max_rss_slope_mb_per_hour < 0:
        parser.error("RSS thresholds must not be negative")
    if args.max_thread_growth < 0:
        parser.error("max-thread-growth must not be negative")
    thresholds = StabilityThresholds(
        max_rss_growth_bytes=int(args.max_rss_growth_mb * 1024 * 1024),
        max_rss_slope_bytes_per_hour=int(args.max_rss_slope_mb_per_hour * 1024 * 1024),
        max_thread_growth=args.max_thread_growth,
    )
    writer = AtomicReportWriter(args.report)
    stop = Event()

    def request_stop(_signal_number: int, _frame: object) -> None:
        stop.set()

    try:
        monitor = ProcessStabilityMonitor(
            args.pid,
            thresholds,
            warmup_seconds=args.warmup_minutes * 60.0,
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied) as error:
        parser.error(f"target process is unavailable: {type(error).__name__}")

    previous_handlers = {
        signal.SIGINT: signal.getsignal(signal.SIGINT),
        signal.SIGTERM: signal.getsignal(signal.SIGTERM),
    }
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        started = monotonic()
        terminal_status = StabilityStatus.PASSED
        terminal_reason: str | None = None
        while True:
            elapsed = monotonic() - started
            if stop.is_set():
                terminal_status = StabilityStatus.INTERRUPTED
                terminal_reason = "Soak monitor was interrupted"
                break
            if elapsed >= duration_seconds:
                break
            try:
                monitor.sample(elapsed)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                terminal_status = StabilityStatus.TARGET_EXITED
                terminal_reason = "Target process exited during soak test"
                break
            except psutil.AccessDenied:
                terminal_status = StabilityStatus.TARGET_UNAVAILABLE
                terminal_reason = "Target process became unavailable during soak test"
                break
            writer.write(monitor.report(elapsed))
            stop.wait(min(interval_seconds, duration_seconds - elapsed))

        elapsed = monotonic() - started
        report = monitor.report(elapsed, terminal_status, reason=terminal_reason)
        writer.write(report)
        print(json.dumps(report.as_dict(), ensure_ascii=False))
        if report.status is StabilityStatus.PASSED:
            return 0
        if report.status is StabilityStatus.INTERRUPTED:
            return 130
        return 2
    finally:
        for signal_number, handler in previous_handlers.items():
            signal.signal(signal_number, handler)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
