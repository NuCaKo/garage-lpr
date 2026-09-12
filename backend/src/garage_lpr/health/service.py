from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy import Engine, text

from garage_lpr.camera.domain import CameraRuntimeState
from garage_lpr.camera.manager import CameraManager
from garage_lpr.events.service import EventService
from garage_lpr.gate.manager import GateManager
from garage_lpr.health.resources import ResourceMonitor
from garage_lpr.inference.domain import InferenceRuntimeState
from garage_lpr.inference.manager import InferenceManager
from garage_lpr.storage.service import SnapshotService

DISK_DEGRADED_PERCENT = 90.0
DISK_UNHEALTHY_PERCENT = 98.0
DISK_DEGRADED_FREE_BYTES = 5 * 1024**3
DISK_UNHEALTHY_FREE_BYTES = 1024**3


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class ComponentHealth(BaseModel):
    state: HealthState
    detail: str


class SystemHealth(BaseModel):
    state: HealthState
    timestamp: datetime
    components: dict[str, ComponentHealth]


class HealthService:
    def __init__(
        self,
        engine: Engine,
        camera_manager: CameraManager,
        inference_manager: InferenceManager,
        gate_manager: GateManager,
        event_service: EventService,
        snapshot_service: SnapshotService,
        resource_monitor: ResourceMonitor,
    ) -> None:
        self._engine = engine
        self._camera_manager = camera_manager
        self._inference_manager = inference_manager
        self._gate_manager = gate_manager
        self._event_service = event_service
        self._snapshot_service = snapshot_service
        self._resource_monitor = resource_monitor

    def snapshot(self) -> SystemHealth:
        database = self._database_health()
        components = {
            "api": ComponentHealth(state=HealthState.HEALTHY, detail="İstek kabul ediyor"),
            "database": database,
            "camera": self._camera_health(),
            "detector": self._inference_health("detector"),
            "ocr": self._inference_health("ocr"),
            "gate": self._gate_health(),
            "events": self._event_health(),
            "storage": self._storage_health(),
            "disk": self._disk_health(),
        }
        states = {component.state for component in components.values()}
        overall = (
            HealthState.UNHEALTHY
            if HealthState.UNHEALTHY in states
            else HealthState.DEGRADED
            if HealthState.DEGRADED in states
            else HealthState.HEALTHY
        )
        return SystemHealth(state=overall, timestamp=datetime.now(UTC), components=components)

    def _database_health(self) -> ComponentHealth:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return ComponentHealth(state=HealthState.HEALTHY, detail="Bağlantı kullanılabilir")
        except Exception:
            return ComponentHealth(state=HealthState.UNHEALTHY, detail="Bağlantı kurulamadı")

    def _camera_health(self) -> ComponentHealth:
        snapshots = self._camera_manager.snapshots()
        if not snapshots:
            return ComponentHealth(
                state=HealthState.DEGRADED,
                detail="Aktif kamera yapılandırılmadı",
            )
        connected = sum(item.state is CameraRuntimeState.CONNECTED for item in snapshots)
        if connected == len(snapshots):
            return ComponentHealth(
                state=HealthState.HEALTHY,
                detail=f"{connected} kamera görüntü sağlıyor",
            )
        unavailable = any(item.state is CameraRuntimeState.UNAVAILABLE for item in snapshots)
        return ComponentHealth(
            state=HealthState.UNHEALTHY if unavailable else HealthState.DEGRADED,
            detail=f"{connected}/{len(snapshots)} kamera görüntü sağlıyor",
        )

    def _inference_health(self, component: str) -> ComponentHealth:
        state, detail = self._inference_manager.component_state(component)
        if state is InferenceRuntimeState.ERROR:
            health = HealthState.UNHEALTHY
        elif state is InferenceRuntimeState.CONFIGURATION_REQUIRED:
            health = HealthState.DEGRADED
        else:
            health = HealthState.HEALTHY
        return ComponentHealth(state=health, detail=detail)

    def _gate_health(self) -> ComponentHealth:
        snapshots = self._gate_manager.snapshots()
        if not snapshots:
            return ComponentHealth(
                state=HealthState.DEGRADED,
                detail="Aktif gate controller yapılandırılmadı",
            )
        healthy = sum(snapshot.healthy for snapshot in snapshots)
        return ComponentHealth(
            state=(HealthState.HEALTHY if healthy == len(snapshots) else HealthState.UNHEALTHY),
            detail=f"{healthy}/{len(snapshots)} gate controller kullanılabilir",
        )

    def _event_health(self) -> ComponentHealth:
        snapshot = self._event_service.snapshot()
        if not snapshot.running:
            return ComponentHealth(
                state=HealthState.UNHEALTHY,
                detail="Event audit worker çalışmıyor",
            )
        if snapshot.last_error:
            return ComponentHealth(
                state=HealthState.DEGRADED,
                detail=(
                    f"{snapshot.persisted} olay kalıcı; "
                    f"{snapshot.failed} başarısız, {snapshot.dropped} düşürüldü; "
                    f"son hata: {snapshot.last_error}"
                ),
            )
        return ComponentHealth(
            state=HealthState.HEALTHY,
            detail=(
                f"{snapshot.persisted} olay kalıcı · {snapshot.pruned} eski kayıt temizlendi · "
                f"kuyruk {snapshot.queue_size}"
            ),
        )

    def _storage_health(self) -> ComponentHealth:
        snapshot = self._snapshot_service.snapshot()
        return ComponentHealth(
            state=HealthState.HEALTHY if snapshot.healthy else HealthState.DEGRADED,
            detail=snapshot.detail,
        )

    def _disk_health(self) -> ComponentHealth:
        snapshot = self._resource_monitor.snapshot()
        if (
            snapshot.disk_percent >= DISK_UNHEALTHY_PERCENT
            or snapshot.disk_free_bytes <= DISK_UNHEALTHY_FREE_BYTES
        ):
            state = HealthState.UNHEALTHY
        elif (
            snapshot.disk_percent >= DISK_DEGRADED_PERCENT
            or snapshot.disk_free_bytes <= DISK_DEGRADED_FREE_BYTES
        ):
            state = HealthState.DEGRADED
        else:
            state = HealthState.HEALTHY
        free_gib = snapshot.disk_free_bytes / 1024**3
        return ComponentHealth(
            state=state,
            detail=f"%{snapshot.disk_percent:.1f} kullanım · {free_gib:.1f} GiB boş",
        )
