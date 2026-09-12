import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from time import monotonic, sleep

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from garage_lpr.database.repositories.events import EventRepository
from garage_lpr.events.broker import LiveEventBroker
from garage_lpr.events.domain import EventServiceSnapshot, OperationalEvent

PERSIST_RETRY_DELAYS_SECONDS = (0.1, 0.5, 1.0)
RETENTION_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


class EventService:
    """Persists audit events on one bounded worker without blocking inference."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        broker: LiveEventBroker,
        queue_capacity: int = 256,
        retention_days: int = 90,
    ) -> None:
        self._session_factory = session_factory
        self._broker = broker
        self._queue: Queue[OperationalEvent] = Queue(maxsize=queue_capacity)
        self._queue_capacity = queue_capacity
        self._lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._persisted = 0
        self._pruned = 0
        self._dropped = 0
        self._failed = 0
        self._retention_days = retention_days
        self._last_retention_check: float | None = None
        self._last_error: str | None = None
        self._logger = logging.getLogger("garage_lpr.events")

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._stop.clear()
            thread = Thread(target=self._run, name="event-audit-worker", daemon=True)
            self._thread = thread
        try:
            thread.start()
        except Exception:
            with self._lock:
                self._thread = None
            raise

    def publish(self, event: OperationalEvent) -> bool:
        with self._lock:
            accepting = self._thread is not None and not self._stop.is_set()
        if not accepting:
            self._record_drop("EVENT_SERVICE_NOT_RUNNING")
            return False
        try:
            self._queue.put_nowait(event)
            return True
        except Full:
            self._record_drop("EVENT_QUEUE_FULL")
            return False

    def configure_retention(self, retention_days: int) -> None:
        if not 1 <= retention_days <= 3650:
            raise ValueError("Event retention must be between 1 and 3650 days")
        with self._lock:
            if self._retention_days != retention_days:
                self._retention_days = retention_days
                self._last_retention_check = None

    def snapshot(self) -> EventServiceSnapshot:
        with self._lock:
            return EventServiceSnapshot(
                running=(
                    self._thread is not None and self._thread.is_alive() and not self._stop.is_set()
                ),
                queue_size=self._queue.qsize(),
                queue_capacity=self._queue_capacity,
                persisted=self._persisted,
                pruned=self._pruned,
                dropped=self._dropped,
                failed=self._failed,
                retention_days=self._retention_days,
                subscriber_count=self._broker.subscriber_count,
                last_error=self._last_error,
            )

    def shutdown(self, timeout_seconds: float = 5.0) -> None:
        with self._lock:
            thread = self._thread
            self._stop.set()
        if thread is None:
            return
        thread.join(timeout_seconds)
        with self._lock:
            if thread.is_alive():
                self._last_error = "Event audit worker did not stop within timeout"
            else:
                self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set() or not self._queue.empty():
            try:
                event = self._queue.get(timeout=0.25)
            except Empty:
                continue
            try:
                if self._persist_with_retry(event):
                    self._prune_if_due()
                    try:
                        self._broker.publish(event)
                    except Exception as error:
                        self._logger.error(
                            "live_event_publish_failed",
                            extra={"metadata": {"error_type": type(error).__name__}},
                        )
            finally:
                self._queue.task_done()

    def _persist_with_retry(self, event: OperationalEvent) -> bool:
        attempts = len(PERSIST_RETRY_DELAYS_SECONDS) + 1
        for attempt in range(attempts):
            session: Session | None = None
            try:
                session = self._session_factory()
                EventRepository(session).persist(event)
                with self._lock:
                    self._persisted += 1
                    self._last_error = None
                return True
            except SQLAlchemyError as error:
                if session is not None:
                    session.rollback()
                if attempt < len(PERSIST_RETRY_DELAYS_SECONDS):
                    sleep(PERSIST_RETRY_DELAYS_SECONDS[attempt])
                    continue
                self._record_failure(type(error).__name__)
            except Exception as error:
                if session is not None:
                    session.rollback()
                self._record_failure(type(error).__name__)
                break
            finally:
                if session is not None:
                    session.close()
        return False

    def _prune_if_due(self) -> None:
        now = monotonic()
        with self._lock:
            if (
                self._last_retention_check is not None
                and now - self._last_retention_check < RETENTION_CHECK_INTERVAL_SECONDS
            ):
                return
            self._last_retention_check = now
            retention_days = self._retention_days

        session: Session | None = None
        try:
            session = self._session_factory()
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            pruned = EventRepository(session).prune_older_than(cutoff)
            with self._lock:
                self._pruned += pruned
            if pruned:
                self._logger.info(
                    "event_retention_completed",
                    extra={"metadata": {"pruned": pruned, "retention_days": retention_days}},
                )
        except Exception as error:
            if session is not None:
                session.rollback()
            self._record_failure(f"RETENTION_{type(error).__name__}")
        finally:
            if session is not None:
                session.close()

    def _record_drop(self, detail: str) -> None:
        with self._lock:
            self._dropped += 1
            self._last_error = detail
        self._logger.error("event_dropped", extra={"metadata": {"reason": detail}})

    def _record_failure(self, error_type: str) -> None:
        with self._lock:
            self._failed += 1
            self._last_error = error_type
        self._logger.error(
            "event_persistence_failed", extra={"metadata": {"error_type": error_type}}
        )
