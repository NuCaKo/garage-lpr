import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from threading import enumerate as enumerate_threads
from time import monotonic, sleep

import psutil
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from garage_lpr.camera.buffer import LatestFrameBuffer
from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.domain import CameraRuntimeConfiguration
from garage_lpr.camera.stream import CameraStreamLoop
from garage_lpr.config.settings import BootstrapSettings
from garage_lpr.database.lifecycle import upgrade_database
from garage_lpr.database.models import RecognitionEvent
from garage_lpr.database.repositories.events import EventRepository
from garage_lpr.database.session import create_database_engine, create_session_factory
from garage_lpr.events.broker import LiveEventBroker
from garage_lpr.events.domain import OperationalEvent
from garage_lpr.events.service import EventService
from garage_lpr.events.types import EventType
from garage_lpr.gate.contracts import GateCommandResult, GateState
from garage_lpr.gate.manager import GateCommandExecutor
from garage_lpr.main import create_app
from garage_lpr.resilience.domain import (
    ProcessMeasurement,
    StabilityStatus,
    StabilityThresholds,
)
from garage_lpr.resilience.monitor import ProcessStabilityMonitor
from garage_lpr.resilience.reporting import AtomicReportWriter
from garage_lpr.resilience.soak import run


class SequenceProbe:
    def __init__(self, measurements: list[ProcessMeasurement]) -> None:
        self._measurements = iter(measurements)

    def sample(self) -> ProcessMeasurement:
        return next(self._measurements)


def test_stability_monitor_uses_scalar_aggregates_for_stable_process() -> None:
    measurements = [
        ProcessMeasurement(100_000_000, 2.0, 8),
        ProcessMeasurement(101_000_000, 3.0, 8),
        ProcessMeasurement(100_500_000, 1.0, 8),
    ]
    monitor = ProcessStabilityMonitor(
        42,
        StabilityThresholds(
            max_rss_growth_bytes=10_000_000,
            max_rss_slope_bytes_per_hour=100_000_000,
            max_thread_growth=1,
        ),
        warmup_seconds=10,
        probe=SequenceProbe(measurements),
    )

    monitor.sample(0)
    monitor.sample(10)
    monitor.sample(70)
    report = monitor.report(70, StabilityStatus.PASSED)

    assert report.status is StabilityStatus.PASSED
    assert report.sample_count == 3
    assert report.evaluated_sample_count == 2
    assert report.baseline_rss_bytes == 101_000_000
    assert report.latest_rss_bytes == 100_500_000
    assert report.reasons == ()


def test_stability_monitor_fails_on_growth_slope_and_threads() -> None:
    monitor = ProcessStabilityMonitor(
        42,
        StabilityThresholds(
            max_rss_growth_bytes=500,
            max_rss_slope_bytes_per_hour=1000,
            max_thread_growth=1,
        ),
        warmup_seconds=0,
        probe=SequenceProbe(
            [
                ProcessMeasurement(1000, 1.0, 2),
                ProcessMeasurement(2000, 2.0, 5),
            ]
        ),
    )

    monitor.sample(0)
    monitor.sample(60)
    report = monitor.report(60, StabilityStatus.PASSED)

    assert report.status is StabilityStatus.FAILED
    assert len(report.reasons) == 3
    assert report.rss_growth_bytes == 1000
    assert report.thread_growth == 3


def test_atomic_report_writer_replaces_one_bounded_file(tmp_path: Path) -> None:
    monitor = ProcessStabilityMonitor(
        42,
        StabilityThresholds(),
        warmup_seconds=0,
        probe=SequenceProbe(
            [
                ProcessMeasurement(1000, 1.0, 2),
                ProcessMeasurement(1000, 1.0, 2),
            ]
        ),
    )
    output = tmp_path / "latest.json"
    writer = AtomicReportWriter(output)

    monitor.sample(0)
    writer.write(monitor.report(0))
    monitor.sample(60)
    writer.write(monitor.report(60, StabilityStatus.PASSED))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "PASSED"
    assert payload["sample_count"] == 2
    assert not output.with_suffix(".json.tmp").exists()


class ReconnectStopSignal:
    def __init__(self, attempts: int) -> None:
        self._attempts = attempts
        self.waits: list[float] = []

    def is_set(self) -> bool:
        return len(self.waits) >= self._attempts

    def wait(self, timeout: float) -> bool:
        self.waits.append(timeout)
        return self.is_set()


class AlwaysFailingProvider:
    def __init__(self) -> None:
        self.closed = False

    def connect(self) -> None:
        raise ConnectionError("offline")

    def read(self) -> CameraFrame | None:
        return None

    def close(self) -> None:
        self.closed = True

    def healthy(self) -> bool:
        return False


def test_reconnect_soak_reuses_one_loop_and_caps_backoff() -> None:
    stop = ReconnectStopSignal(attempts=100)
    providers: list[AlwaysFailingProvider] = []

    def provider_builder() -> AlwaysFailingProvider:
        provider = AlwaysFailingProvider()
        providers.append(provider)
        return provider

    loop = CameraStreamLoop(
        CameraRuntimeConfiguration(
            camera_id=1,
            stream_url="rtsp://camera.invalid/live",
            username=None,
            password=None,
            reconnect_schedule_seconds=(1, 2, 5, 10, 30),
        ),
        provider_builder,
        lambda _frame: None,
        lambda _state, _detail: None,
    )

    loop.run(stop)

    assert len(providers) == 100
    assert all(provider.closed for provider in providers)
    assert stop.waits[:6] == [1, 2, 5, 10, 30, 30]
    assert set(stop.waits[4:]) == {30}


class BlockingGateController:
    def __init__(self) -> None:
        self.release = Event()
        self.calls = 0

    def open(self) -> GateCommandResult:
        self.calls += 1
        self.release.wait()
        return GateCommandResult(True, "LATE_OPEN")

    def close(self) -> GateCommandResult:
        return GateCommandResult(True, "CLOSED")

    def status(self) -> GateState:
        return GateState.CLOSED

    def health_check(self) -> bool:
        return True


def test_gate_timeout_soak_never_requeues_after_poisoning() -> None:
    executor = GateCommandExecutor()
    controller = BlockingGateController()
    try:
        first = executor.open(controller, timeout_seconds=0.001)
        repeated = [
            executor.open(controller, timeout_seconds=0.001)
            for _ in range(250)
        ]

        assert first.detail == "GATE_COMMAND_TIMEOUT"
        assert all(result.detail == "GATE_EXECUTOR_POISONED" for result in repeated)
        assert controller.calls == 1
    finally:
        controller.release.set()
        executor.shutdown()


def test_latest_frame_pressure_keeps_only_newest_frame() -> None:
    buffer = LatestFrameBuffer()
    for sequence in range(1, 10_001):
        buffer.put(CameraFrame(object(), sequence, sequence, 1280, 720))

    latest = buffer.latest()
    assert latest is not None and latest.sequence == 10_000
    assert buffer.replaced_frames == 9_999


def test_sqlite_wal_handles_bounded_concurrent_event_writers(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'contention.db'}"
    upgrade_database(database_url)
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    def write_events(worker_id: int) -> int:
        for item in range(20):
            session = session_factory()
            try:
                EventRepository(session).persist(
                    OperationalEvent.create(
                        EventType.PLATE_DETECTED,
                        "CONTENTION_TEST",
                        metadata={"worker": worker_id, "item": item},
                    )
                )
            finally:
                session.close()
        return 20

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            written = sum(executor.map(write_events, range(4)))
        session = session_factory()
        try:
            persisted = int(session.scalar(select(func.count(RecognitionEvent.id))) or 0)
        finally:
            session.close()
    finally:
        engine.dispose()

    assert written == 80
    assert persisted == written


def test_soak_cli_runs_short_process_probe_and_writes_final_report(tmp_path: Path) -> None:
    output = tmp_path / "soak.json"

    exit_code = run(
        [
            "--pid",
            str(os.getpid()),
            "--duration-seconds",
            "0.05",
            "--interval-seconds",
            "0.01",
            "--warmup-minutes",
            "0",
            "--max-rss-growth-mb",
            "1000000",
            "--max-rss-slope-mb-per-hour",
            "1000000",
            "--max-thread-growth",
            "1000",
            "--report",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["status"] == "PASSED"
    assert payload["sample_count"] >= 1


def test_event_queue_pressure_stays_bounded_and_reports_drops(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue-pressure.db'}"
    upgrade_database(database_url)
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    release_factory = Event()

    def delayed_session_factory() -> Session:
        release_factory.wait(timeout=1)
        return session_factory()

    service = EventService(delayed_session_factory, LiveEventBroker(), queue_capacity=4)
    service.start()
    try:
        accepted = [
            service.publish(OperationalEvent.create(EventType.PLATE_DETECTED, "PRESSURE"))
            for _ in range(100)
        ]
        snapshot = service.snapshot()

        assert snapshot.queue_size <= snapshot.queue_capacity == 4
        assert not all(accepted)
        assert snapshot.dropped > 0
    finally:
        release_factory.set()
        service.shutdown(timeout_seconds=2)
        engine.dispose()


def test_repeated_application_lifecycle_leaves_no_managed_workers(
    test_settings: BootstrapSettings,
) -> None:
    with TestClient(create_app(test_settings)):
        pass
    baseline_process_threads = psutil.Process().num_threads()

    for _ in range(10):
        with TestClient(create_app(test_settings)):
            pass

    deadline = monotonic() + 1
    managed_prefixes = ("camera-", "inference-worker", "event-audit-worker", "gate-command")
    while monotonic() < deadline:
        managed = [
            thread.name
            for thread in enumerate_threads()
            if thread.name.startswith(managed_prefixes)
        ]
        if not managed:
            break
        sleep(0.01)

    assert managed == []
    assert psutil.Process().num_threads() <= baseline_process_threads + 1
