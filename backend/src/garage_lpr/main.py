import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from garage_lpr import __version__
from garage_lpr.api.router import api_router
from garage_lpr.auth.limiter import LoginAttemptLimiter
from garage_lpr.auth.passwords import Argon2PasswordService
from garage_lpr.auth.service import AuthenticationService
from garage_lpr.camera.domain import CameraRuntimeConfiguration, CameraRuntimeState
from garage_lpr.camera.manager import CameraManager
from garage_lpr.camera.preview import JpegPreviewEncoder
from garage_lpr.camera.rtsp import OpenCVCaptureFactory, RTSPCameraProvider
from garage_lpr.camera.secrets import SecretCipher
from garage_lpr.camera.service import CameraService
from garage_lpr.camera.testing import CameraConnectionTester
from garage_lpr.config.service import ConfigurationService
from garage_lpr.config.settings import BootstrapSettings, RuntimeSettings
from garage_lpr.database.lifecycle import upgrade_database
from garage_lpr.database.repositories.cameras import CameraRepository
from garage_lpr.database.repositories.gates import GateControllerRepository
from garage_lpr.database.session import create_database_engine, create_session_factory
from garage_lpr.events.broker import LiveEventBroker
from garage_lpr.events.domain import OperationalEvent
from garage_lpr.events.recorder import OperationalEventRecorder
from garage_lpr.events.service import EventService
from garage_lpr.events.types import EventType
from garage_lpr.gate.manager import GateManager
from garage_lpr.gate.orchestration_factory import GateOrchestratorFactory
from garage_lpr.gate.service import GateControllerService
from garage_lpr.health.resources import ResourceMonitor
from garage_lpr.health.service import HealthService
from garage_lpr.inference.factory import ProductionPipelineFactory
from garage_lpr.inference.manager import InferenceManager
from garage_lpr.inference.runtime import ONNXRuntimeSessionFactory
from garage_lpr.logging.setup import configure_logging
from garage_lpr.recognition.factory import RecognitionServiceFactory
from garage_lpr.security.headers import SecurityHeadersMiddleware
from garage_lpr.storage.local import LocalSnapshotStorage
from garage_lpr.storage.service import SnapshotService


def create_app(settings: BootstrapSettings | None = None) -> FastAPI:
    bootstrap = settings or BootstrapSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(bootstrap)
        logger = logging.getLogger("garage_lpr.lifecycle")
        logger.info("system_started", extra={"metadata": {"version": __version__}})
        if bootstrap.auto_migrate:
            upgrade_database(bootstrap.database_url)

        engine = create_database_engine(bootstrap.database_url)
        session_factory = create_session_factory(engine)
        authentication_service = AuthenticationService(
            Argon2PasswordService(testing=bootstrap.environment == "test"),
            LoginAttemptLimiter(bootstrap.login_max_attempts, bootstrap.login_lock_seconds),
            bootstrap.session_ttl_hours,
        )
        capture_factory = OpenCVCaptureFactory()
        live_event_broker = LiveEventBroker(
            bootstrap.live_event_queue_capacity,
            bootstrap.max_live_event_subscribers,
        )
        event_service = EventService(
            session_factory,
            live_event_broker,
            bootstrap.event_queue_capacity,
        )
        event_service.start()
        snapshot_storage = LocalSnapshotStorage(
            bootstrap.snapshot_directory, bootstrap.preview_jpeg_quality
        )
        snapshot_service = SnapshotService(
            snapshot_storage,
            enabled=False,
            retention_days=30,
        )
        resource_monitor = ResourceMonitor(bootstrap.snapshot_directory)

        def camera_state_observer(
            camera_id: int,
            previous: CameraRuntimeState | None,
            current: CameraRuntimeState,
            detail: str,
        ) -> None:
            event_type = None
            if current is CameraRuntimeState.CONNECTED:
                event_type = EventType.CAMERA_CONNECTED
            elif previous is CameraRuntimeState.CONNECTED:
                event_type = EventType.CAMERA_DISCONNECTED
            if event_type is not None:
                event_service.publish(
                    OperationalEvent.create(
                        event_type,
                        current.value,
                        camera_id=camera_id,
                        reason=detail,
                        metadata={"previous_state": previous.value if previous else None},
                    )
                )

        def provider_factory(configuration: CameraRuntimeConfiguration) -> RTSPCameraProvider:
            return RTSPCameraProvider(configuration, capture_factory)

        camera_manager = CameraManager(
            provider_factory,
            bootstrap.max_active_cameras,
            camera_state_observer,
        )
        gate_manager = GateManager()

        def event_recorder_builder(runtime: RuntimeSettings) -> OperationalEventRecorder:
            event_service.configure_retention(runtime.event_retention_days)
            snapshot_service.configure(
                enabled=runtime.snapshot_enabled,
                retention_days=runtime.snapshot_retention_days,
            )
            return OperationalEventRecorder(
                event_service,
                snapshot_service,
                runtime.plate_detection_event_interval_seconds,
            )

        inference_manager = InferenceManager(
            camera_manager,
            ProductionPipelineFactory(ONNXRuntimeSessionFactory()).create,
            RecognitionServiceFactory(session_factory).create,
            GateOrchestratorFactory(session_factory, gate_manager, camera_manager).create,
            event_recorder_builder,
        )
        secret_cipher = SecretCipher(bootstrap.secret_key_path)
        app.state.settings = bootstrap
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.authentication_service = authentication_service
        app.state.allowed_websocket_origins = {
            *bootstrap.cors_origins,
            f"http://localhost:{bootstrap.port}",
            f"http://127.0.0.1:{bootstrap.port}",
        }
        app.state.secret_cipher = secret_cipher
        app.state.camera_manager = camera_manager
        app.state.gate_manager = gate_manager
        app.state.event_service = event_service
        app.state.live_event_broker = live_event_broker
        app.state.snapshot_service = snapshot_service
        app.state.resource_monitor = resource_monitor
        app.state.inference_manager = inference_manager
        app.state.preview_encoder = JpegPreviewEncoder(bootstrap.preview_jpeg_quality)
        app.state.camera_connection_tester = CameraConnectionTester(provider_factory)
        app.state.health_service = HealthService(
            engine,
            camera_manager,
            inference_manager,
            gate_manager,
            event_service,
            snapshot_service,
            resource_monitor,
        )

        event_service.publish(
            OperationalEvent.create(
                EventType.SYSTEM_STARTED,
                "RUNNING",
                metadata={"version": __version__},
            )
        )

        session = session_factory()
        try:
            camera_service = CameraService(
                CameraRepository(session), secret_cipher, bootstrap.max_active_cameras
            )
            gate_service = GateControllerService(GateControllerRepository(session))
            for gate in gate_service.list_all():
                if gate.active:
                    try:
                        gate_manager.apply(gate_service.runtime_configuration(gate))
                    except Exception as error:
                        logger.error(
                            "gate_start_failed",
                            extra={
                                "metadata": {
                                    "gate_controller_id": gate.id,
                                    "error_type": type(error).__name__,
                                }
                            },
                        )
            runtime_settings = ConfigurationService(session).get_runtime_settings()
            event_service.configure_retention(runtime_settings.event_retention_days)
            snapshot_service.configure(
                enabled=runtime_settings.snapshot_enabled,
                retention_days=runtime_settings.snapshot_retention_days,
            )
            inference_manager.configure(runtime_settings)
            for camera in camera_service.list_all():
                if camera.active:
                    try:
                        camera_manager.apply(camera_service.runtime_configuration(camera))
                    except Exception as error:
                        camera_manager.mark_unavailable(camera.id, "Camera could not be started")
                        logger.error(
                            "camera_start_failed",
                            extra={
                                "metadata": {
                                    "camera_id": camera.id,
                                    "error_type": type(error).__name__,
                                }
                            },
                        )
                inference_manager.apply_camera(camera_service.inference_configuration(camera))
        finally:
            session.close()
        try:
            yield
        finally:
            try:
                inference_manager.shutdown()
            except Exception as error:
                logger.error(
                    "inference_shutdown_failed",
                    extra={"metadata": {"error_type": type(error).__name__}},
                )
            try:
                camera_manager.shutdown()
            except Exception as error:
                logger.error(
                    "camera_shutdown_failed",
                    extra={"metadata": {"error_type": type(error).__name__}},
                )
            gate_manager.shutdown()
            event_service.publish(OperationalEvent.create(EventType.SYSTEM_STOPPED, "STOPPED"))
            event_service.shutdown()
            engine.dispose()
            logger.info("system_stopped")

    app = FastAPI(
        title=bootstrap.app_name,
        version=__version__,
        docs_url="/docs" if bootstrap.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=bootstrap.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "PUT", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        production=bootstrap.environment == "production",
    )
    app.include_router(api_router)

    if (
        bootstrap.environment == "production"
        and (bootstrap.frontend_dist_directory / "index.html").is_file()
    ):
        app.mount(
            "/",
            StaticFiles(directory=bootstrap.frontend_dist_directory, html=True),
            name="frontend",
        )
    else:

        @app.get("/", include_in_schema=False)
        def root() -> dict[str, str]:
            return {"name": bootstrap.app_name, "version": __version__, "status": "running"}

    return app
