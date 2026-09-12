from collections.abc import Callable

from sqlalchemy.orm import Session

from garage_lpr.access.authorization import DatabaseAuthorizationResolver
from garage_lpr.access.cooldown import CooldownManager
from garage_lpr.config.settings import RuntimeSettings
from garage_lpr.recognition.service import RecognitionService
from garage_lpr.recognition.tracker import IoUTracker


class RecognitionServiceFactory:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create(self, settings: RuntimeSettings) -> RecognitionService:
        return RecognitionService(
            tracker=IoUTracker(
                iou_threshold=settings.tracking_iou_threshold,
                max_idle_ms=settings.tracking_max_idle_ms,
                max_tracks=settings.max_active_tracks,
            ),
            authorization=DatabaseAuthorizationResolver(
                self._session_factory,
                settings.local_timezone,
            ),
            cooldown=CooldownManager(
                settings.gate_cooldown_seconds,
                settings.global_gate_cooldown_seconds,
            ),
            min_confidence=settings.recognition_min_confidence,
            required_confirmations=settings.required_confirmations,
            confirmation_window_ms=settings.confirmation_window_ms,
            maintenance_mode=settings.maintenance_mode,
        )
