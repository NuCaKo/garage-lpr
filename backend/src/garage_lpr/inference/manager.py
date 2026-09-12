import logging
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Event, Lock, Thread

from garage_lpr.camera.manager import CameraManager
from garage_lpr.config.settings import RuntimeSettings
from garage_lpr.detection.pipeline import DetectionPipeline
from garage_lpr.detection.sampler import FrameSampler
from garage_lpr.events.recorder import OperationalEventRecorder
from garage_lpr.gate.orchestration import GateOrchestrationResult, GateOrchestrator
from garage_lpr.inference.domain import (
    InferenceCameraConfiguration,
    InferenceRuntimeSnapshot,
    InferenceRuntimeState,
)
from garage_lpr.inference.factory import ComponentInitializationError, PipelineBundle
from garage_lpr.inference.metrics import InferenceMetrics
from garage_lpr.recognition.service import RecognitionService

PipelineBuilder = Callable[[RuntimeSettings], PipelineBundle]
RecognitionBuilder = Callable[[RuntimeSettings], RecognitionService]
GateOrchestratorBuilder = Callable[[RuntimeSettings], GateOrchestrator]
EventRecorderBuilder = Callable[[RuntimeSettings], OperationalEventRecorder]


class InferenceWorkerStopError(RuntimeError):
    pass


class InferenceManager:
    """Runs one fixed inference worker over bounded latest-frame camera inputs."""

    def __init__(
        self,
        camera_manager: CameraManager,
        pipeline_builder: PipelineBuilder,
        recognition_builder: RecognitionBuilder | None = None,
        gate_orchestrator_builder: GateOrchestratorBuilder | None = None,
        event_recorder_builder: EventRecorderBuilder | None = None,
    ) -> None:
        self._camera_manager = camera_manager
        self._pipeline_builder = pipeline_builder
        self._recognition_builder = recognition_builder
        self._gate_orchestrator_builder = gate_orchestrator_builder
        self._event_recorder_builder = event_recorder_builder
        self._metrics = InferenceMetrics()
        self._lock = Lock()
        self._cameras: dict[int, InferenceCameraConfiguration] = {}
        self._bundle: PipelineBundle | None = None
        self._recognition: RecognitionService | None = None
        self._gate_orchestrator: GateOrchestrator | None = None
        self._event_recorder: OperationalEventRecorder | None = None
        self._state = InferenceRuntimeState.CONFIGURATION_REQUIRED
        self._detail = "Inference models are not configured"
        self._failed_component: str | None = None
        self._stop_event: Event | None = None
        self._thread: Thread | None = None
        self._logger = logging.getLogger("garage_lpr.inference")
        self._detection_fps_cap = 5.0

    def configure(self, settings: RuntimeSettings) -> None:
        self._stop_worker()
        with self._lock:
            self._detection_fps_cap = settings.detection_fps
        try:
            bundle = self._pipeline_builder(settings)
            recognition = (
                self._recognition_builder(settings)
                if self._recognition_builder is not None
                else None
            )
            gate_orchestrator = (
                self._gate_orchestrator_builder(settings)
                if self._gate_orchestrator_builder is not None
                else None
            )
            event_recorder = (
                self._event_recorder_builder(settings)
                if self._event_recorder_builder is not None
                else None
            )
        except ComponentInitializationError as error:
            with self._lock:
                self._bundle = None
                self._recognition = None
                self._gate_orchestrator = None
                self._event_recorder = None
                self._failed_component = error.component
                self._state = InferenceRuntimeState.CONFIGURATION_REQUIRED
                self._detail = error.detail
            self._logger.warning(
                "inference_configuration_required",
                extra={
                    "metadata": {
                        "component": error.component,
                        "error_type": type(error).__name__,
                    }
                },
            )
            return
        except Exception as error:
            with self._lock:
                self._bundle = None
                self._recognition = None
                self._gate_orchestrator = None
                self._event_recorder = None
                self._failed_component = "inference"
                self._state = InferenceRuntimeState.ERROR
                self._detail = "Inference pipeline could not be initialized"
            self._logger.error(
                "inference_initialization_failed",
                extra={"metadata": {"error_type": type(error).__name__}},
            )
            return
        with self._lock:
            self._bundle = bundle
            self._recognition = recognition
            self._gate_orchestrator = gate_orchestrator
            self._event_recorder = event_recorder
            self._failed_component = None
            self._state = InferenceRuntimeState.READY
            self._detail = "Models loaded; waiting for an active camera"
        self._ensure_worker()

    def apply_camera(self, configuration: InferenceCameraConfiguration) -> None:
        self._stop_worker()
        with self._lock:
            self._cameras[configuration.camera_id] = configuration
        self._ensure_worker()

    def remove_camera(self, camera_id: int) -> None:
        self._stop_worker()
        with self._lock:
            self._cameras.pop(camera_id, None)
        self._ensure_worker()

    def snapshot(self) -> InferenceRuntimeSnapshot:
        with self._lock:
            state = self._state
            detail = self._detail
            bundle = self._bundle
            active_count = sum(camera.active for camera in self._cameras.values())
        return self._metrics.snapshot(
            state=state,
            detail=detail,
            detector_provider=bundle.detector_provider if bundle else None,
            ocr_provider=bundle.ocr_provider if bundle else None,
            active_camera_count=active_count,
        )

    def component_state(self, component: str) -> tuple[InferenceRuntimeState, str]:
        with self._lock:
            if self._failed_component in {component, "inference"}:
                return self._state, self._detail
            if self._bundle is None:
                return (
                    InferenceRuntimeState.CONFIGURATION_REQUIRED,
                    f"{component.upper()} model is not loaded",
                )
            return self._state, self._detail

    def shutdown(self) -> None:
        self._stop_worker()
        with self._lock:
            self._state = InferenceRuntimeState.STOPPED
            self._detail = "Inference worker stopped"

    def _ensure_worker(self) -> None:
        with self._lock:
            active = any(camera.active for camera in self._cameras.values())
            if self._bundle is None or not active or self._thread is not None:
                if self._bundle is not None and not active:
                    self._state = InferenceRuntimeState.READY
                    self._detail = "Models loaded; waiting for an active camera"
                return
            bundle = self._bundle
            recognition = self._recognition
            gate_orchestrator = self._gate_orchestrator
            event_recorder = self._event_recorder
            stop_event = Event()
            thread = Thread(
                target=self._run,
                args=(
                    stop_event,
                    bundle.pipeline,
                    recognition,
                    gate_orchestrator,
                    event_recorder,
                ),
                name="inference-worker",
                daemon=True,
            )
            self._stop_event = stop_event
            self._thread = thread
            self._state = InferenceRuntimeState.READY
            self._detail = "Waiting for a camera frame"
        try:
            thread.start()
        except Exception:
            with self._lock:
                self._thread = None
                self._stop_event = None
                self._state = InferenceRuntimeState.ERROR
                self._detail = "Inference worker could not be started"
            raise

    def _stop_worker(self) -> None:
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
        if thread is None or stop_event is None:
            return
        stop_event.set()
        thread.join(timeout=10.0)
        if thread.is_alive():
            with self._lock:
                self._state = InferenceRuntimeState.ERROR
                self._detail = "Inference worker did not stop within its timeout"
            raise InferenceWorkerStopError(self._detail)
        with self._lock:
            self._thread = None
            self._stop_event = None

    def _run(
        self,
        stop_event: Event,
        pipeline: DetectionPipeline,
        recognition: RecognitionService | None,
        gate_orchestrator: GateOrchestrator | None,
        event_recorder: OperationalEventRecorder | None,
    ) -> None:
        samplers: dict[int, FrameSampler] = {}
        last_sequences: dict[int, int] = {}
        while not stop_event.is_set():
            with self._lock:
                cameras = tuple(camera for camera in self._cameras.values() if camera.active)
                detection_fps_cap = self._detection_fps_cap
            if not cameras:
                stop_event.wait(1.0)
                continue
            minimum_wait = 1.0
            for camera in cameras:
                sampler = samplers.get(camera.camera_id)
                if sampler is None:
                    sampler = FrameSampler(min(camera.detection_fps, detection_fps_cap))
                    samplers[camera.camera_id] = sampler
                frame = self._camera_manager.latest_frame(
                    camera.camera_id, last_sequences.get(camera.camera_id)
                )
                if frame is None or not sampler.should_process(frame):
                    minimum_wait = min(minimum_wait, sampler.interval_seconds)
                    continue
                last_sequences[camera.camera_id] = frame.sequence
                try:
                    result = pipeline.process(camera.camera_id, frame, camera.roi)
                except Exception as error:
                    if event_recorder is not None:
                        event_recorder.record_error(
                            camera.camera_id, type(error).__name__, frame.image
                        )
                    self._logger.error(
                        "inference_pipeline_failed",
                        extra={
                            "metadata": {
                                "camera_id": camera.camera_id,
                                "error_type": type(error).__name__,
                            }
                        },
                    )
                    with self._lock:
                        self._state = InferenceRuntimeState.ERROR
                        self._detail = "Inference pipeline stopped after an error"
                    return
                self._metrics.record(result)
                batch = None
                gate_results: tuple[GateOrchestrationResult, ...] = ()
                if recognition is not None:
                    try:
                        batch = recognition.process(
                            result,
                            frame.captured_monotonic_ns,
                            datetime.now(UTC),
                        )
                    except Exception as error:
                        if event_recorder is not None:
                            event_recorder.record_error(
                                camera.camera_id, type(error).__name__, frame.image
                            )
                        self._logger.error(
                            "recognition_pipeline_failed",
                            extra={
                                "metadata": {
                                    "camera_id": camera.camera_id,
                                    "error_type": type(error).__name__,
                                }
                            },
                        )
                        with self._lock:
                            self._state = InferenceRuntimeState.ERROR
                            self._detail = "Recognition pipeline stopped after an error"
                        return
                    self._metrics.record_recognition(batch)
                    if gate_orchestrator is not None:
                        try:
                            gate_results = gate_orchestrator.process_batch(batch)
                            self._metrics.record_gate(gate_results)
                        except Exception as error:
                            if event_recorder is not None:
                                event_recorder.record_error(
                                    camera.camera_id, type(error).__name__, frame.image
                                )
                            self._logger.error(
                                "gate_orchestration_failed",
                                extra={
                                    "metadata": {
                                        "camera_id": camera.camera_id,
                                        "error_type": type(error).__name__,
                                    }
                                },
                            )
                    if event_recorder is not None:
                        try:
                            event_recorder.record(
                                result,
                                batch,
                                gate_results,
                                frame.image,
                                frame.captured_monotonic_ns,
                            )
                        except Exception as error:
                            self._logger.error(
                                "event_recording_failed",
                                extra={
                                    "metadata": {
                                        "camera_id": camera.camera_id,
                                        "error_type": type(error).__name__,
                                    }
                                },
                            )
                with self._lock:
                    self._state = InferenceRuntimeState.RUNNING
                    self._detail = "Detection, OCR and temporal recognition are running"
                minimum_wait = min(
                    minimum_wait,
                    max(0.01, sampler.seconds_until_due()),
                )
            stop_event.wait(minimum_wait)
