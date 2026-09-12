import type { AccessRule, AccessRuleWrite, Camera, CameraConnectionResult, CameraWrite, CurrentUser, EventPage, GateConnectionResult, GateController, GateControllerWrite, InferenceMetrics, ResourceMetrics, RuntimeSettings, SetupStatus, SystemHealth, Vehicle, VehicleWrite } from './types'

const API_ROOT = '/api/v1'
let csrfCookieName = 'garage_lpr_csrf'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? 'GET'
  const csrfToken = !['GET', 'HEAD', 'OPTIONS'].includes(method)
    ? readCookie(csrfCookieName)
    : null
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') {
      window.dispatchEvent(new Event('garage-lpr:unauthorized'))
    }
    const payload = await response.json().catch(() => null) as { detail?: unknown } | null
    throw new Error(formatApiError(payload?.detail, response.status))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  setupStatus: async (signal?: AbortSignal) => {
    const status = await request<SetupStatus>('/auth/setup-status', { signal })
    csrfCookieName = status.csrf_cookie_name
    return status
  },
  setupAdmin: (username: string, password: string, passwordConfirmation: string) =>
    request<CurrentUser>('/auth/setup', {
      method: 'POST',
      body: JSON.stringify({ username, password, password_confirmation: passwordConfirmation }),
    }),
  login: (username: string, password: string) =>
    request<CurrentUser>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  currentUser: (signal?: AbortSignal) => request<CurrentUser>('/auth/me', { signal }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  health: (signal?: AbortSignal) => request<SystemHealth>('/health', { signal }),
  inferenceMetrics: (signal?: AbortSignal) =>
    request<InferenceMetrics>('/metrics/inference', { signal }),
  resourceMetrics: (signal?: AbortSignal) =>
    request<ResourceMetrics>('/metrics/resources', { signal }),
  events: (query = '', signal?: AbortSignal) =>
    request<EventPage>(`/events${query ? `?${query}` : ''}`, { signal }),
  eventSocketUrl: () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${API_ROOT}/events/live`
  },
  settings: (signal?: AbortSignal) => request<RuntimeSettings>('/system-settings', { signal }),
  saveSettings: (settings: RuntimeSettings) =>
    request<RuntimeSettings>('/system-settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),
  cameras: (signal?: AbortSignal) => request<Camera[]>('/cameras', { signal }),
  createCamera: (camera: CameraWrite) =>
    request<Camera>('/cameras', { method: 'POST', body: JSON.stringify(camera) }),
  updateCamera: (cameraId: number, camera: CameraWrite) =>
    request<Camera>(`/cameras/${cameraId}`, { method: 'PUT', body: JSON.stringify(camera) }),
  deleteCamera: (cameraId: number) => request<void>(`/cameras/${cameraId}`, { method: 'DELETE' }),
  testCamera: (cameraId: number) =>
    request<CameraConnectionResult>(`/cameras/${cameraId}/test-connection`, { method: 'POST' }),
  cameraPreviewUrl: (cameraId: number, nonce: number) =>
    `${API_ROOT}/cameras/${cameraId}/preview.jpg?t=${nonce}`,
  vehicles: (signal?: AbortSignal) => request<Vehicle[]>('/vehicles', { signal }),
  createVehicle: (vehicle: VehicleWrite) =>
    request<Vehicle>('/vehicles', { method: 'POST', body: JSON.stringify(vehicle) }),
  updateVehicle: (vehicleId: number, vehicle: VehicleWrite) =>
    request<Vehicle>(`/vehicles/${vehicleId}`, { method: 'PUT', body: JSON.stringify(vehicle) }),
  deleteVehicle: (vehicleId: number) =>
    request<void>(`/vehicles/${vehicleId}`, { method: 'DELETE' }),
  gateControllers: (signal?: AbortSignal) =>
    request<GateController[]>('/gate-controllers', { signal }),
  createGateController: (gate: GateControllerWrite) =>
    request<GateController>('/gate-controllers', { method: 'POST', body: JSON.stringify(gate) }),
  updateGateController: (gateId: number, gate: GateControllerWrite) =>
    request<GateController>(`/gate-controllers/${gateId}`, { method: 'PUT', body: JSON.stringify(gate) }),
  deleteGateController: (gateId: number) =>
    request<void>(`/gate-controllers/${gateId}`, { method: 'DELETE' }),
  testGateController: (gateId: number) =>
    request<GateConnectionResult>(`/gate-controllers/${gateId}/test-connection`, { method: 'POST' }),
  accessRules: (signal?: AbortSignal) => request<AccessRule[]>('/access-rules', { signal }),
  createAccessRule: (rule: AccessRuleWrite) =>
    request<AccessRule>('/access-rules', { method: 'POST', body: JSON.stringify(rule) }),
  updateAccessRule: (ruleId: number, rule: AccessRuleWrite) =>
    request<AccessRule>(`/access-rules/${ruleId}`, { method: 'PUT', body: JSON.stringify(rule) }),
  deleteAccessRule: (ruleId: number) =>
    request<void>(`/access-rules/${ruleId}`, { method: 'DELETE' }),
}

function readCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`
  const entry = document.cookie.split('; ').find((item) => item.startsWith(prefix))
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null
}

function formatApiError(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (!item || typeof item !== 'object') return []
      const message = 'msg' in item ? item.msg : null
      return typeof message === 'string' ? [message] : []
    })
    if (messages.length) return messages.join(' · ')
  }
  return `API isteği başarısız (${status})`
}
