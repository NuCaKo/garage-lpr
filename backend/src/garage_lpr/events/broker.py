import asyncio
from contextlib import suppress
from dataclasses import dataclass
from threading import Lock

from garage_lpr.events.domain import OperationalEvent


@dataclass(frozen=True, slots=True)
class LiveEventSubscription:
    subscription_id: int
    queue: asyncio.Queue[OperationalEvent]


@dataclass(slots=True)
class _Subscriber:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[OperationalEvent]


class LiveEventBroker:
    """Thread-safe, bounded fan-out from the audit worker to WebSocket clients."""

    def __init__(self, queue_capacity: int = 64, max_subscribers: int = 16) -> None:
        self._queue_capacity = queue_capacity
        self._max_subscribers = max_subscribers
        self._lock = Lock()
        self._next_id = 1
        self._subscribers: dict[int, _Subscriber] = {}

    def subscribe(self) -> LiveEventSubscription:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[OperationalEvent] = asyncio.Queue(self._queue_capacity)
        with self._lock:
            if len(self._subscribers) >= self._max_subscribers:
                raise RuntimeError("Live event subscriber limit reached")
            subscription_id = self._next_id
            self._next_id += 1
            self._subscribers[subscription_id] = _Subscriber(loop, queue)
        return LiveEventSubscription(subscription_id, queue)

    def unsubscribe(self, subscription_id: int) -> None:
        with self._lock:
            self._subscribers.pop(subscription_id, None)

    def publish(self, event: OperationalEvent) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers.items())
        stale_subscribers = []
        for subscription_id, subscriber in subscribers:
            try:
                subscriber.loop.call_soon_threadsafe(self._offer_latest, subscriber.queue, event)
            except RuntimeError:
                stale_subscribers.append(subscription_id)
        for subscription_id in stale_subscribers:
            self.unsubscribe(subscription_id)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    @staticmethod
    def _offer_latest(queue: asyncio.Queue[OperationalEvent], event: OperationalEvent) -> None:
        if queue.full():
            with suppress(asyncio.QueueEmpty):
                queue.get_nowait()
        with suppress(asyncio.QueueFull):
            queue.put_nowait(event)
