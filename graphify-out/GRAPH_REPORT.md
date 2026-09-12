# Graph Report - .  (2026-09-12)

## Corpus Check
- 2 files · ~46,493 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1680 nodes · 2878 edges · 153 communities (97 shown, 56 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 461 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- CameraManager
- OperationalEventRecorder
- ProcessMeasurement
- RTSPCameraProvider
- models.py
- GateManager
- AuthenticationService
- auth.py
- ONNXCTCOCRProvider
- AccessRule
- Camera
- GateControllerRepository
- InferenceManager
- EventService
- ReconnectBackoff
- ONNXPlateDetector
- SnapshotService
- LatestFrameBuffer
- devDependencies
- CameraWrite
- DetectionPipeline
- Vehicle
- DetectionPipelineResult
- compilerOptions
- RuntimeSettings
- authorization.py
- ValueError
- CooldownManager
- BootstrapSettings
- Garage LPR Stability Test
- IoUTracker
- Dashboard.tsx
- RecognitionService
- runtime root
- App.tsx
- compilerOptions
- authorize
- FrameSampler
- test deployment.py
- Cameras.tsx
- types.ts
- service
- CameraFrames
- TurkishPlateNormalizer
- api.ts
- Icons.tsx
- GarageLPRWindowsService
- SecurityHeadersMiddleware
- .process
- GateController
- .run
- TemporalPlateValidator
- Authorization
- Audit Event Service
- Phase 6 Continue Query
- Vehicles.tsx
- .test
- session.py
- AccessRules.tsx
- Events.tsx
- JsonFormatter
- Build Garage LPR Windows Installer
- Model Tensor Contracts
- run
- OCRProvider
- SuccessfulConnectionTester
- Phase 2 Report
- Active Windows Installer Workflow
- factory with providers
- test settings api.py
- Target Recognition Data Flow
- Windows EXE Field Installation
- Phase 4 Safe Decision Report
- Phase 5 Fail-safe Gate Orchestration
- Architecture Boundaries
- base.py
- test health api.py
- Garage LPR Design System
- Configure Once Run Continuously
- Windows Installer Implementation
- AuthorizationStatus
- test inference metrics are bounded
- Opaque Database-Backed Session
- tsconfig.json
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- init .py
- ADR-0001 Foundation Stack Decision
- Existing Decision and Persistence Contracts
- Existing Gate Contracts
- dev.sh script
- graphify-watch.sh
- soak-test.sh script
- CameraFrame
- CameraRuntimeConfiguration
- CameraRuntimeSnapshot
- CameraRuntimeState
- ProviderFactory
- CameraConnectionResult
- BaseModel
- ndarray
- Engine
- RuntimeError
- RuntimeSettings
- DetectionPipeline
- AuthorizationStatus
- TestClient
- CameraManager
- CameraRepository
- Windows SCM Service
- Phase 3 Implementation Guidance
- Phase 7 Security Plan
- NormalizedROI
- Path
- garage-lpr
- Request
- Session

## God Nodes (most connected - your core abstractions)
1. `CameraManager` - 36 edges
2. `RuntimeSettings` - 25 edges
3. `EventService` - 22 edges
4. `Vehicle` - 22 edges
5. `Camera` - 20 edges
6. `OperationalEventRecorder` - 19 edges
7. `compilerOptions` - 18 edges
8. `IoUTracker` - 18 edges
9. `BootstrapSettings` - 18 edges
10. `TurkishPlateNormalizer` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Protocol Adapter Contracts` --conceptually_related_to--> `Architecture Boundaries`  [INFERRED]
  docs/phase-reports/phase-1.md → AGENTS.md
- `Garage LPR HTML Shell` --conceptually_related_to--> `Garage LPR Design System`  [INFERRED]
  frontend/index.html → design-system/garage-lpr/MASTER.md
- `test_reconnect_backoff_caps_and_resets()` --calls--> `ReconnectBackoff`  [INFERRED]
  backend/tests/test_camera_primitives.py → backend/src/garage_lpr/camera/backoff.py
- `Existing Camera and Configuration Contracts` --conceptually_related_to--> `Camera Management, Test, and Preview API`  [INFERRED]
  graphify-out/memory/query_20260910_131753_phase_2_rtsp_camera_live_preview_reconnect_roi_imp.md → docs/phase-reports/phase-2.md
- `_get_or_404()` --references--> `Vehicle`  [EXTRACTED]
  backend/src/garage_lpr/api/routes/vehicles.py → frontend/src/types.ts

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Windows Installer Build and Delivery Flow** — installer_requirements_build_pyinstaller_6, installer_ci_windows_installer_windows_installer_workflow, installer_ci_windows_installer_installer_artifact, installer_readme_single_file_setup_package [INFERRED 0.95]
- **Windows Field Safety and Persistence** — docs_deployment_local_only_security_boundary, docs_deployment_windows_service_recovery, docs_deployment_persistent_data_backup, docs_deployment_seventy_two_hour_field_test [EXTRACTED 1.00]
- **Phase 8 Field Acceptance Flow** — docs_stability_test_seventy_two_hour_soak_test, docs_stability_test_constant_memory_process_monitoring, docs_stability_test_controlled_failure_scenarios, docs_stability_test_operational_acceptance_checklist [EXTRACTED 1.00]
- **Phase 7 Authentication Protection Flow** — docs_architecture_first_admin_bootstrap, docs_architecture_bounded_login_rate_limiter, docs_architecture_opaque_session_csrf_digests, docs_architecture_admin_authorization_boundary, docs_architecture_websocket_origin_allowlist, docs_phase_reports_phase_7_double_submit_server_digest_csrf, docs_phase_reports_phase_7_single_admin_session [INFERRED 0.85]
- **Phase 6 Query Source Context** — graphify_out_memory_query_20260911_083102_phase_6_ya_devam_et_recognition_service, graphify_out_memory_query_20260911_083102_phase_6_ya_devam_et_gate_orchestrator, graphify_out_memory_query_20260911_083102_phase_6_ya_devam_et_recognition_event, graphify_out_memory_query_20260911_083102_phase_6_ya_devam_et_access_event, graphify_out_memory_query_20260911_083102_phase_6_ya_devam_et_health_service, graphify_out_memory_query_20260911_083102_phase_6_ya_devam_et_dashboard [EXTRACTED 1.00]
- **Phase 5 to Phase 6 Observability Handoff** — docs_phase_reports_phase_5_gate_metrics, docs_phase_reports_phase_5_phase_6_handoff, docs_phases_phase_6_operations [INFERRED 0.95]
- **Phase 4 to Phase 5 Gate Boundary** — docs_architecture_authorized_pending_gate, docs_architecture_phase_4_no_gate_open, docs_phase_reports_phase_4_phase_5_handoff, docs_phases_phase_5_gate [INFERRED 0.95]
- **Phase 3 Model Contract Validation** — docs_architecture_production_pipeline_factory, models_readme_detector_contract, models_readme_ocr_contract, docs_architecture_configuration_required_degraded_mode [INFERRED 0.95]
- **Phase 3 to Phase 4 Safety Boundary** — docs_architecture_turkish_plate_normalizer, docs_phase_reports_phase_3_phase_4_handoff, docs_phases_phase_4_decision [INFERRED 0.95]
- **Phase 2 Camera Configuration Flow** — graphify_out_memory_query_20260910_131753_phase_2_rtsp_camera_live_preview_reconnect_roi_imp_existing_camera_configuration_contracts, docs_phase_reports_phase_2_camera_management_api, docs_architecture_normalized_roi, docs_architecture_camera_credential_boundary [INFERRED 0.85]
- **Garage LPR Phase 1 Foundation Record** — readme_phase_1_foundation, docs_adr_0001_foundation_stack_foundation_stack_decision, docs_phase_reports_phase_1_phase_1_report [INFERRED 0.95]

## Communities (153 total, 56 thin omitted)

### Community 0 - "CameraManager"
Cohesion: 0.05
Nodes (46): CameraManager, CameraWorkerStopError, RuntimeError, Owns a bounded set of long-lived camera workers and capacity-one buffers., _Worker, DatabaseGateTargetResolver, GateOrchestratorFactory, RuntimeSettings (+38 more)

### Community 1 - "OperationalEventRecorder"
Cohesion: 0.06
Nodes (48): _as_utc(), EventListRead, EventRead, BaseModel, datetime, OperationalEvent, RecognitionEvent, EventRepository (+40 more)

### Community 2 - "ProcessMeasurement"
Cohesion: 0.07
Nodes (33): ProcessMeasurement, StabilityReport, StabilityStatus, StabilityThresholds, ProcessProbe, ProcessStabilityMonitor, PsutilProcessProbe, Constant-memory online mean and linear regression accumulator. (+25 more)

### Community 3 - "RTSPCameraProvider"
Cohesion: 0.06
Nodes (19): CameraFrame, CameraProvider, Protocol, CameraRuntimeConfiguration, JpegPreviewEncoder, CameraConnectionError, CaptureDevice, CaptureFactory (+11 more)

### Community 4 - "models.py"
Cohesion: 0.07
Nodes (37): ConfigurationService, RuntimeSettings, Session, AccessEvent, AccessRule, Camera, CameraType, GateControllerConfig (+29 more)

### Community 5 - "GateManager"
Cohesion: 0.07
Nodes (24): GateRuntimeConfiguration, GateRuntimeSnapshot, GateControllerFactory, ValueError, Builds supported adapters without leaking persistence models into drivers., UnsupportedGateControllerError, GateCommandExecutor, GateManager (+16 more)

### Community 6 - "AuthenticationService"
Cohesion: 0.09
Nodes (25): get_database_session(), DatabaseSession, Request, Session, require_admin(), require_current_user(), AuthenticatedPrincipal, IssuedSession (+17 more)

### Community 7 - "auth.py"
Cohesion: 0.08
Nodes (39): _clear_auth_cookies(), _client_identity(), login(), logout(), me(), _publish_auth_event(), DatabaseSession, Request (+31 more)

### Community 8 - "ONNXCTCOCRProvider"
Cohesion: 0.08
Nodes (27): InferenceConfigurationError, InferenceSession, ONNXRuntimeSessionFactory, Any, Path, Protocol, RuntimeError, Creates conservative, sequential ORT sessions with explicit provider order. (+19 more)

### Community 9 - "AccessRule"
Cohesion: 0.09
Nodes (26): AccessRuleConflictError, AccessRuleReferenceError, AccessRuleService, CameraRepository, ValueError, create_access_rule(), delete_access_rule(), _get_or_404() (+18 more)

### Community 10 - "Camera"
Cohesion: 0.09
Nodes (26): camera_preview(), create_camera(), delete_camera(), _get_or_404(), list_cameras(), DatabaseSession, Request, Response (+18 more)

### Community 11 - "GateControllerRepository"
Cohesion: 0.09
Nodes (25): create_gate_controller(), delete_gate_controller(), _get_or_404(), list_gate_controllers(), DatabaseSession, GateControllerConfig, Request, Response (+17 more)

### Community 12 - "InferenceManager"
Cohesion: 0.06
Nodes (23): LiveEventBroker, LiveEventSubscription, OperationalEvent, Thread-safe, bounded fan-out from the audit worker to WebSocket clients., _Subscriber, Session, InferenceManager, InferenceWorkerStopError (+15 more)

### Community 13 - "EventService"
Cohesion: 0.09
Nodes (16): EventServiceSnapshot, EventService, OperationalEvent, Persists audit events on one bounded worker without blocking inference., Path, Samples process and host scalars only when the low-frequency API is read., ResourceMonitor, ResourceSnapshot (+8 more)

### Community 14 - "ReconnectBackoff"
Cohesion: 0.09
Nodes (14): ReconnectBackoff, CameraStreamLoop, CameraRuntimeConfiguration, Protocol, Runs one camera in one bounded lifecycle loop; it never creates threads itself., StopSignal, ControlledStopSignal, FakeProvider (+6 more)

### Community 15 - "ONNXPlateDetector"
Cohesion: 0.13
Nodes (17): _intersection_over_union(), ONNXDetectorConfiguration, ONNXPlateDetector, Any, BoundingBox, Small adapter for explicit XYXY or YOLOv8-style ONNX detector outputs., _validate_input_shape(), DetectorSession (+9 more)

### Community 16 - "SnapshotService"
Cohesion: 0.09
Nodes (13): Any, Path, Protocol, SnapshotStorage, LocalSnapshotStorage, Any, Path, Writes event-only JPEG snapshots and prunes them by file age. (+5 more)

### Community 17 - "LatestFrameBuffer"
Cohesion: 0.09
Nodes (12): LatestFrameBuffer, Drop a stale frame before a camera worker is restarted., A capacity-one buffer: producers never wait and stale frames never accumulate., Path, SecretCipher, _frame(), Path, test_camera_password_is_encrypted_at_rest() (+4 more)

### Community 18 - "devDependencies"
Cohesion: 0.08
Nodes (24): dependencies, react, react-dom, devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+16 more)

### Community 19 - "CameraWrite"
Cohesion: 0.16
Nodes (16): CameraConnectionRead, CameraCreate, CameraRead, CameraUpdate, CameraWrite, NormalizedROISchema, BaseModel, CameraConnectionResult (+8 more)

### Community 20 - "DetectionPipeline"
Cohesion: 0.16
Nodes (15): BoundingBox, PlateDetection, PlateDetector, Any, Protocol, DetectionPipeline, DetectionPipelineConfiguration, Runs detector on ROI and OCR only on bounded plate crops. (+7 more)

### Community 21 - "Vehicle"
Cohesion: 0.16
Nodes (5): InvalidVehiclePlateError, VehicleService, Session, VehicleRepository, Vehicle

### Community 22 - "DetectionPipelineResult"
Cohesion: 0.17
Nodes (9): DetectionPipelineResult, main(), OfflineVideoRunner, Feeds a recording through the same pipeline without retaining video frames., Capture, CV2, Pipeline, Any (+1 more)

### Community 23 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+11 more)

### Community 24 - "RuntimeSettings"
Cohesion: 0.15
Nodes (10): Validated settings editable from the local administration UI., RuntimeSettings, ComponentInitializationError, ProductionPipelineFactory, test_runtime_settings_enforce_low_frequency_metrics(), test_runtime_settings_normalize_and_validate_model_contract_values(), test_runtime_settings_require_multiple_confirmations(), BaseModel (+2 more)

### Community 25 - "authorization.py"
Cohesion: 0.22
Nodes (11): _as_aware(), AuthorizationDecision, AuthorizationResolver, AuthorizationService, DatabaseAuthorizationResolver, _inside_schedule(), datetime, Protocol (+3 more)

### Community 26 - "ValueError"
Cohesion: 0.17
Nodes (6): BaseModel, VehicleCreate, VehicleUpdate, VehicleWrite, Self, ValueError

### Community 27 - "CooldownManager"
Cohesion: 0.15
Nodes (7): CooldownDecision, CooldownManager, Atomically reserves bounded plate/global trigger windows., RuntimeSettings, Session, RecognitionServiceFactory, test_cooldown_enforces_plate_and_global_windows()

### Community 28 - "BootstrapSettings"
Cohesion: 0.17
Nodes (12): BootstrapSettings, Immutable process bootstrap values loaded before the database is available., create_app(), main(), FastAPI, client(), Path, TestClient (+4 more)

### Community 29 - "Garage LPR Stability Test"
Cohesion: 0.19
Nodes (16): Idle Smoke Measurement, Phase 8 Resilience Report, Profiling and Stress Infrastructure, Real Hardware Validation Gap, Pending 72-Hour Field Run, Phase 8 Resilience, Automatic Acceptance Thresholds, Constant-Memory Process Monitoring (+8 more)

### Community 30 - "IoUTracker"
Cohesion: 0.21
Nodes (9): _intersection_over_union(), IoUTracker, BoundingBox, Bounded, appearance-free tracker for short-lived plate observations., _Track, TrackerUpdate, test_iou_tracker_does_not_share_tracks_between_cameras(), test_iou_tracker_reuses_identity_and_expires_stale_track() (+1 more)

### Community 31 - "Dashboard.tsx"
Cohesion: 0.19
Nodes (11): Dashboard(), formatBytes(), formatMetric(), pipeline, componentLabel(), formatBytes(), formatDuration(), SystemHealthPage() (+3 more)

### Community 32 - "RecognitionService"
Cohesion: 0.21
Nodes (9): CooldownStatus, StrEnum, datetime, DetectionPipelineResult, StrEnum, Turns crop OCR candidates into bounded, fail-safe access decisions., RecognitionBatch, RecognitionOutcome (+1 more)

### Community 33 - "runtime root"
Cohesion: 0.21
Nodes (11): Path, Return the read-only application resource root.      PyInstaller exposes bundled, Return the writable root for database, secrets, logs, and snapshots., repository_root(), runtime_root(), _model_path(), Path, test_model_lookup_prefers_writable_runtime_payload() (+3 more)

### Community 34 - "App.tsx"
Cohesion: 0.22
Nodes (11): api, App(), AuthenticatedApp(), IconComponent, initialPage(), navigation, PageId, renderPage() (+3 more)

### Community 35 - "compilerOptions"
Cohesion: 0.14
Nodes (13): compilerOptions, allowImportingTsExtensions, lib, module, moduleDetection, moduleResolution, noEmit, skipLibCheck (+5 more)

### Community 36 - "authorize"
Cohesion: 0.29
Nodes (9): AuthorizationStatus, Session, _authorize(), datetime, test_authorization_handles_cross_midnight_schedule_by_start_day(), test_authorization_returns_required_statuses(), _vehicle(), Vehicles (+1 more)

### Community 37 - "FrameSampler"
Cohesion: 0.19
Nodes (7): FrameSampler, CameraFrame, Accepts at most one latest frame per configured detection interval., _frame(), CameraFrame, test_sampler_limits_detection_rate_without_queuing_frames(), test_sampler_recovers_when_monotonic_source_restarts()

### Community 38 - "test deployment.py"
Cohesion: 0.27
Nodes (10): Path, _settings(), test_auth_responses_are_not_cached_and_have_security_headers(), test_bundled_resource_root_uses_pyinstaller_meipass(), test_cors_preflight_allows_only_configured_origin(), test_production_serves_built_frontend_and_disables_api_docs(), test_access_rule_crud_validates_references_and_duplicates(), test_gate_target_resolver_prefers_exact_camera_and_rejects_ambiguity() (+2 more)

### Community 39 - "Cameras.tsx"
Cohesion: 0.21
Nodes (7): RoiEditor(), CamerasPage(), EMPTY_CAMERA, parseSchedule(), selectCamera(), updateRoi(), CameraWrite

### Community 40 - "types.ts"
Cohesion: 0.20
Nodes (5): ComponentHealth, EventPage, HealthState, RuntimeSettings, SetupStatus

### Community 41 - "service"
Cohesion: 0.44
Nodes (9): create_vehicle(), delete_vehicle(), _get_or_404(), list_vehicles(), Session, _service(), update_vehicle(), VehicleRead (+1 more)

### Community 42 - "CameraFrames"
Cohesion: 0.31
Nodes (7): InferenceCameraConfiguration, PipelineBundle, CameraFrames, Pipeline, Any, CameraFrame, test_inference_manager_uses_one_worker_and_scalar_metrics()

### Community 43 - "TurkishPlateNormalizer"
Cohesion: 0.27
Nodes (7): NormalizedPlate, Normalizes formatting and corrects ambiguous glyphs only by plate position., TurkishPlateNormalizer, test_normalizer_corrects_ambiguous_glyph_only_in_letter_context(), test_normalizer_corrects_province_and_suffix_in_numeric_context(), test_normalizer_rejects_invalid_or_ambiguous_formats(), test_normalizer_removes_formatting_without_glyph_changes()

### Community 44 - "api.ts"
Cohesion: 0.29
Nodes (9): formatApiError(), readCookie(), request(), EMPTY_GATE, GateControllersPage(), selectGate(), showError(), GateConnectionResult (+1 more)

### Community 46 - "GarageLPRWindowsService"
Cohesion: 0.24
Nodes (5): Any, GarageLPRWindowsService, main(), Expose the service type for a platform-neutral import smoke test., service_class()

### Community 47 - "SecurityHeadersMiddleware"
Cohesion: 0.20
Nodes (6): ASGIApp, Apply small, deterministic browser hardening headers without BaseHTTP overhead., SecurityHeadersMiddleware, Receive, Scope, Send

### Community 48 - ".process"
Cohesion: 0.27
Nodes (7): _crop_roi(), _elapsed_ms(), PlateRecognitionCandidate, CameraFrame, Any, DetectionPipeline, NormalizedROI

### Community 49 - "GateController"
Cohesion: 0.27
Nodes (5): GateCommandResult, GateController, GateState, Protocol, StrEnum

### Community 50 - ".run"
Cohesion: 0.29
Nodes (5): OfflineRunSummary, Path, Protocol, VideoCapture, ResultHandler

### Community 51 - "TemporalPlateValidator"
Cohesion: 0.27
Nodes (6): _Observation, Confirms an exact normalized plate repeatedly within a bounded window., TemporalConfirmation, TemporalPlateValidator, test_temporal_validator_drops_old_and_low_confidence_observations(), test_temporal_validator_requires_repeated_confident_plate()

### Community 52 - "Authorization"
Cohesion: 0.36
Nodes (7): Authorization, AuthorizationStatus, datetime, DetectionPipelineResult, _result(), test_recognition_authorizes_only_after_temporal_confirmation_and_once_per_track(), test_recognition_maintenance_mode_never_reserves_gate_ready_outcome()

### Community 53 - "Audit Event Service"
Cohesion: 0.20
Nodes (10): Atomic Snapshot Storage, Audit Event Service, Detection Event Sampling, Persist Before Live Publish, Phase 6 Report — Operations, Phase 6 Verification, Phase 7 Security Follow-Up, Phase 8 Field Validation (+2 more)

### Community 54 - "Phase 6 Continue Query"
Cohesion: 0.31
Nodes (10): AccessEvent, Dashboard, Event History API and WebSocket, GateOrchestrator, HealthService, No High-Frequency Polling, Phase 6 Continue Query, Post-Decision Persistence (+2 more)

### Community 55 - "Vehicles.tsx"
Cohesion: 0.31
Nodes (7): DAYS, EMPTY_VEHICLE, selectVehicle(), shortTime(), toggleDay(), VehiclesPage(), VehicleWrite

### Community 56 - ".test"
Cohesion: 0.29
Nodes (5): CameraConnectionTester, _elapsed_ms(), CameraRuntimeConfiguration, ProviderFactory, CameraConnectionResult

### Community 57 - "session.py"
Cohesion: 0.39
Nodes (7): create_database_engine(), create_session_factory(), _ensure_sqlite_parent(), Engine, Session, session_scope(), sessionmaker

### Community 58 - "AccessRules.tsx"
Cohesion: 0.39
Nodes (7): AccessRulesPage(), EMPTY_RULE, gateLabel(), newRule(), selectRule(), vehicleLabel(), AccessRuleWrite

### Community 59 - "Events.tsx"
Cohesion: 0.36
Nodes (7): eventLabel(), EventRow(), EventsPage(), eventTone(), eventTypes, RECONNECT_DELAYS_MS, OperationalEvent

### Community 60 - "JsonFormatter"
Cohesion: 0.38
Nodes (5): configure_logging(), JsonFormatter, Any, _redact(), LogRecord

### Community 61 - "Build Garage LPR Windows Installer"
Cohesion: 0.29
Nodes (7): Program Files and ProgramData Separation, PyInstaller Onedir Service Bundle, Windows Installer Model, Garage LPR Windows Installer Artifact, Build Garage LPR Windows Installer Workflow, Windows Latest Build Runner, PyInstaller 6 Build Dependency

### Community 62 - "Model Tensor Contracts"
Cohesion: 0.29
Nodes (7): Phase 3 Detection and OCR Report, Phase 3 Verification, Phase 4 Decision Handoff, Detector Tensor Contract, Model Tensor Contracts, OCR Tensor Contract, Offline Video Test

### Community 63 - "run"
Cohesion: 0.60
Nodes (5): ArgumentParser, build_parser(), main(), _positive(), run()

### Community 64 - "OCRProvider"
Cohesion: 0.40
Nodes (4): OCRProvider, OCRResult, Any, Protocol

### Community 65 - "SuccessfulConnectionTester"
Cohesion: 0.40
Nodes (3): CameraConnectionResult, SuccessfulConnectionTester, test_camera_connection_result_contains_operational_metrics()

### Community 66 - "Phase 2 Report"
Cohesion: 0.33
Nodes (6): Camera Management, Test, and Preview API, Phase 2 Report, Phase 2 Verification, RTSP OpenCV Provider, Existing Camera and Configuration Contracts, Phase 2 Integration Guidance

### Community 67 - "Active Windows Installer Workflow"
Cohesion: 0.33
Nodes (6): Installer and Checksum Artifact, Windows Installer Build Toolchain, Active Windows Installer Workflow, GitHub Actions Installer Build, Persistent Field Data Preservation, Single File Windows Setup

### Community 68 - "factory with providers"
Cohesion: 0.60
Nodes (4): _factory_with_providers(), test_auto_provider_prefers_cuda_and_cpu_is_explicit_fallback(), test_explicit_cuda_fails_closed_when_provider_is_unavailable(), ONNXRuntimeSessionFactory

### Community 69 - "test settings api.py"
Cohesion: 0.60
Nodes (4): TestClient, test_runtime_settings_are_validated_and_persisted(), test_runtime_settings_start_fail_safe(), test_unsafe_detection_rate_is_rejected()

### Community 70 - "Target Recognition Data Flow"
Cohesion: 0.40
Nodes (5): External System Adapter Boundary, Bounded Latest Frame Processing, Fail Safe Gate Orchestration, Target Recognition Data Flow, Gate Open Safety Boundary

### Community 71 - "Windows EXE Field Installation"
Cohesion: 0.40
Nodes (5): Local Only Deployment Security Boundary, Persistent Data Backup, 72 Hour Field Stability Test, Windows EXE Field Installation, Windows Service Recovery

### Community 72 - "Phase 4 Safe Decision Report"
Cohesion: 0.40
Nodes (5): Phase 4 Safe Decision Report, Phase 4 Verification, Phase 5 Gate Handoff, Recognition Orchestration, Authorized Vehicle Management

### Community 73 - "Phase 5 Fail-safe Gate Orchestration"
Cohesion: 0.40
Nodes (5): Gate Outcome Metrics, Mock Gate Controller Adapter, Phase 5 Fail-safe Gate Orchestration Report, Phase 5 Verification, Phase 6 Operations Handoff

### Community 75 - "Architecture Boundaries"
Cohesion: 0.50
Nodes (4): Architecture Boundaries, Fail-safe Product Invariant, Phase 1 Report, Protocol Adapter Contracts

### Community 76 - "base.py"
Cohesion: 0.50
Nodes (3): Base, TimestampMixin, DeclarativeBase

### Community 77 - "test health api.py"
Cohesion: 0.67
Nodes (3): TestClient, test_health_exposes_database_and_fail_safe_state(), test_root_has_no_operational_controls()

### Community 78 - "Garage LPR Design System"
Cohesion: 0.50
Nodes (4): Accessible Dense Dashboard, Garage LPR Design System, Garage LPR HTML Shell, Main TSX Module Entry

### Community 79 - "Configure Once Run Continuously"
Cohesion: 0.50
Nodes (4): Bounded Soak Monitor, Configure Once Run Continuously, Garage LPR Local Edge System, Windows Installer

### Community 80 - "Windows Installer Implementation"
Cohesion: 0.50
Nodes (4): Onedir Deterministic Service Startup, Uninstall Data Preservation, Windows Installer Implementation, Windows Installer Validation Gap

### Community 87 - "Opaque Database-Backed Session"
Cohesion: 0.67
Nodes (3): Double-Submit Server-Digest CSRF, Opaque Database-Backed Session, Single Admin Session

## Knowledge Gaps
- **115 isolated node(s):** `TimestampMixin`, `IconProps`, `base`, `tsBuildInfoFile`, `target` (+110 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RuntimeSettings` connect `RuntimeSettings` to `CameraManager`, `runtime root`, `models.py`, `CameraFrames`, `InferenceManager`, `.run`, `DetectionPipelineResult`, `CooldownManager`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `Camera` connect `Camera` to `Cameras.tsx`, `types.ts`, `api.ts`, `CameraWrite`, `AccessRules.tsx`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `CameraManager` connect `CameraManager` to `LatestFrameBuffer`, `InferenceManager`, `EventService`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `CameraManager` (e.g. with `DatabaseGateTargetResolver` and `GateOrchestratorFactory`) actually correct?**
  _`CameraManager` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `RuntimeSettings` (e.g. with `ConfigurationService` and `GateOrchestratorFactory`) actually correct?**
  _`RuntimeSettings` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `EventService` (e.g. with `LiveEventBroker` and `EventServiceSnapshot`) actually correct?**
  _`EventService` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Garage LPR edge application.`, `HTTP API transport layer.`, `Versioned route modules.` to the rest of the system?**
  _198 weakly-connected nodes found - possible documentation gaps or missing edges._