export type HealthState = 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY'

export interface SetupStatus {
  setup_required: boolean
  csrf_cookie_name: string
}

export interface CurrentUser {
  id: number
  username: string
  role: 'ADMIN'
  session_expires_at: string
}

export interface ComponentHealth {
  state: HealthState
  detail: string
}

export interface SystemHealth {
  state: HealthState
  timestamp: string
  components: Record<string, ComponentHealth>
}

export interface RuntimeSettings {
  simulation_mode: boolean
  maintenance_mode: boolean
  metrics_poll_interval_seconds: number
  snapshot_enabled: boolean
  snapshot_retention_days: number
  event_retention_days: number
  detection_fps: number
  inference_provider: 'auto' | 'cpu' | 'cuda'
  detector_model_path: string
  detector_output_format: 'xyxy' | 'yolo_v8'
  detector_input_width: number
  detector_input_height: number
  detector_confidence_threshold: number
  detector_iou_threshold: number
  max_plates_per_frame: number
  ocr_model_path: string
  ocr_input_width: number
  ocr_input_height: number
  ocr_input_channels: 1 | 3
  ocr_charset: string
  recognition_min_confidence: number
  required_confirmations: number
  confirmation_window_ms: number
  tracking_iou_threshold: number
  tracking_max_idle_ms: number
  max_active_tracks: number
  local_timezone: string
  gate_cooldown_seconds: number
  global_gate_cooldown_seconds: number
  gate_command_timeout_seconds: number
  plate_detection_event_interval_seconds: number
}

export interface NormalizedROI {
  x: number
  y: number
  width: number
  height: number
}

export interface Camera {
  id: number
  name: string
  camera_type: 'RTSP'
  stream_url: string
  username: string | null
  has_password: boolean
  capture_fps_limit: number
  detection_fps: number
  requested_width: number | null
  requested_height: number | null
  roi: NormalizedROI
  active: boolean
  connection_timeout_seconds: number
  reconnect_schedule_seconds: number[]
  runtime_state: 'STOPPED' | 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'UNAVAILABLE'
  runtime_detail: string
  frames_received: number
  frames_replaced: number
  created_at: string
  updated_at: string
}

export interface CameraWrite {
  name: string
  camera_type: 'RTSP'
  stream_url: string
  username: string | null
  password: string | null
  clear_password?: boolean
  capture_fps_limit: number
  detection_fps: number
  requested_width: number | null
  requested_height: number | null
  roi: NormalizedROI
  active: boolean
  connection_timeout_seconds: number
  reconnect_schedule_seconds: number[]
}

export interface CameraConnectionResult {
  connected: boolean
  latency_ms: number
  resolution: string | null
  fps: number | null
  detail: string
}

export interface InferenceMetrics {
  state: 'STOPPED' | 'CONFIGURATION_REQUIRED' | 'READY' | 'RUNNING' | 'ERROR'
  detail: string
  detector_provider: string | null
  ocr_provider: string | null
  active_camera_count: number
  frames_sampled: number
  plates_detected: number
  ocr_calls: number
  valid_plates: number
  last_plate: string | null
  effective_detection_fps: number
  detection_latency_ms: number
  ocr_latency_ms: number
  total_latency_ms: number
  active_tracks: number
  pending_validations: number
  recognized_plates: number
  access_ready: number
  access_denied: number
  cooldown_suppressed: number
  last_decision_plate: string | null
  last_authorization_status: string | null
  last_recognition_outcome: string | null
  gate_open_success: number
  gate_open_failed: number
  simulated_gate_open: number
  last_gate_outcome: string | null
  frame_buffer_capacity: number
  queue_size: number
}

export interface ResourceMetrics {
  system_cpu_percent: number
  system_ram_percent: number
  system_ram_used_bytes: number
  system_ram_total_bytes: number
  process_cpu_percent: number
  process_rss_bytes: number
  process_thread_count: number
  disk_percent: number
  disk_free_bytes: number
  uptime_seconds: number
}

export interface OperationalEvent {
  event_id: string
  timestamp: string
  event_type: string
  camera_id: number | null
  plate: string | null
  confidence: number | null
  status: string
  vehicle_id: number | null
  gate_controller_id: number | null
  reason: string | null
  metadata: Record<string, unknown>
}

export interface EventPage {
  items: OperationalEvent[]
  total: number
  limit: number
  offset: number
}

export interface Vehicle {
  id: number
  plate: string
  owner: string
  description: string | null
  active: boolean
  valid_from: string | null
  valid_until: string | null
  allowed_days: number[]
  allowed_start_time: string | null
  allowed_end_time: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export type VehicleWrite = Omit<Vehicle, 'id' | 'created_at' | 'updated_at'>

export interface GateController {
  id: number
  name: string
  controller_type: 'MOCK'
  active: boolean
  pulse_ms: number
  configuration: Record<string, unknown>
  runtime_state: 'OPEN' | 'CLOSED' | 'UNKNOWN' | 'UNAVAILABLE'
  healthy: boolean
  runtime_detail: string
  created_at: string
  updated_at: string
}

export type GateControllerWrite = Pick<GateController, 'name' | 'controller_type' | 'active' | 'pulse_ms' | 'configuration'>

export interface GateConnectionResult {
  connected: boolean
  state: string
  detail: string
}

export interface AccessRule {
  id: number
  name: string
  vehicle_id: number
  camera_id: number | null
  gate_controller_id: number
  active: boolean
  created_at: string
  updated_at: string
}

export type AccessRuleWrite = Omit<AccessRule, 'id' | 'created_at' | 'updated_at'>
