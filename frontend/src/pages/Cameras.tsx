import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { RoiEditor } from '../components/RoiEditor'
import type { Camera, CameraConnectionResult, CameraWrite, NormalizedROI } from '../types'

const EMPTY_CAMERA: CameraWrite = {
  name: '', camera_type: 'RTSP', stream_url: '', username: '', password: '',
  capture_fps_limit: 25, detection_fps: 5,
  requested_width: 1280, requested_height: 720,
  roi: { x: 0, y: 0, width: 1, height: 1 }, active: false,
  connection_timeout_seconds: 5, reconnect_schedule_seconds: [1, 2, 5, 10, 30],
}
const CAMERA_STATUS_INTERVAL_MS = 10_000

export function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [form, setForm] = useState<CameraWrite>(EMPTY_CAMERA)
  const [message, setMessage] = useState<string | null>(null)
  const [connection, setConnection] = useState<CameraConnectionResult | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    api.cameras(controller.signal).then((items) => {
      setCameras(items)
      if (items[0]) selectCamera(items[0], setSelectedId, setForm)
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Kameralar alınamadı')
    })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setInterval(() => {
      void api.cameras(controller.signal).then(setCameras).catch(() => undefined)
    }, CAMERA_STATUS_INTERVAL_MS)
    return () => { controller.abort(); window.clearInterval(timer) }
  }, [])

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setMessage(null); setConnection(null)
    try {
      const payload = { ...form, username: form.username || null, password: form.password || null }
      const saved = selectedId === null
        ? await api.createCamera(payload)
        : await api.updateCamera(selectedId, payload)
      setCameras((current) => [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) => a.name.localeCompare(b.name)))
      selectCamera(saved, setSelectedId, setForm)
      setMessage('Kamera yapılandırması kaydedildi.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Kamera kaydedilemedi')
    } finally { setBusy(false) }
  }

  async function testConnection() {
    if (selectedId === null) return
    setBusy(true); setMessage(null); setConnection(null)
    try { setConnection(await api.testCamera(selectedId)) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Bağlantı testi başarısız') }
    finally { setBusy(false) }
  }

  async function remove() {
    if (selectedId === null || !window.confirm('Bu kamera yapılandırması silinsin mi?')) return
    setBusy(true)
    try {
      await api.deleteCamera(selectedId)
      setCameras((current) => current.filter((item) => item.id !== selectedId))
      setSelectedId(null); setForm(EMPTY_CAMERA); setConnection(null)
      setMessage('Kamera silindi.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Kamera silinemedi') }
    finally { setBusy(false) }
  }

  const selected = cameras.find((camera) => camera.id === selectedId)
  return <>
    <section className="page-heading"><div><p className="eyebrow">Phase 2 · RTSP</p><h1>Kameralar</h1><p>Bağlantı, düşük gecikmeli frame alma ve normalize detection alanını tek noktadan yönetin.</p></div><button type="button" className="secondary-button" onClick={() => { setSelectedId(null); setForm(EMPTY_CAMERA); setConnection(null); setMessage(null) }}>Yeni kamera</button></section>
    {message && <div className="alert" role="status">{message}</div>}
    <div className="camera-layout">
      <aside className="panel camera-list" aria-label="Kamera listesi">
        <div className="panel-heading"><div><p className="eyebrow">Kaynaklar</p><h2>Tanımlı kameralar</h2></div><span className="muted">{cameras.length}</span></div>
        {cameras.length === 0 && <p className="muted">Henüz kamera eklenmedi.</p>}
        {cameras.map((camera) => <button type="button" key={camera.id} className={camera.id === selectedId ? 'camera-item selected' : 'camera-item'} onClick={() => { selectCamera(camera, setSelectedId, setForm); setConnection(null); setMessage(null) }}>
          <span><strong>{camera.name}</strong><small title={camera.stream_url}>{camera.stream_url}</small></span><RuntimeDot state={camera.runtime_state}/>
        </button>)}
      </aside>
      <form className="camera-form" onSubmit={save}>
        <section className="panel form-grid">
          <div className="panel-heading form-span"><div><p className="eyebrow">Bağlantı</p><h2>{selected ? selected.name : 'Yeni RTSP kamera'}</h2></div>{selected && <span className="runtime-label"><RuntimeDot state={selected.runtime_state}/>{selected.runtime_detail}</span>}</div>
          <TextField label="Kamera adı" value={form.name} required onChange={(name) => setForm({ ...form, name })}/>
          <label className="field"><span>Kamera tipi</span><select value="RTSP" disabled><option>RTSP</option></select></label>
          <label className="field form-span"><span>RTSP URL</span><input type="url" placeholder="rtsp://192.168.1.20/stream" required value={form.stream_url} onChange={(event) => setForm({ ...form, stream_url: event.target.value })}/><small>Kullanıcı adı ve parolayı URL içine yazmayın.</small></label>
          <TextField label="Kullanıcı adı" value={form.username ?? ''} onChange={(username) => setForm({ ...form, username })}/>
          <label className="field"><span>Parola</span><input type="password" autoComplete="new-password" value={form.password ?? ''} placeholder={selected?.has_password ? 'Değiştirmek için yeni parola' : ''} onChange={(event) => setForm({ ...form, password: event.target.value })}/></label>
          <NumberField label="Capture FPS limiti" value={form.capture_fps_limit} min={1} max={60} step={1} onChange={(capture_fps_limit) => setForm({ ...form, capture_fps_limit })}/>
          <NumberField label="Detection FPS" value={form.detection_fps} min={0.5} max={15} step={0.5} onChange={(detection_fps) => setForm({ ...form, detection_fps })}/>
          <NumberField label="Genişlik" value={form.requested_width ?? 1280} min={160} max={7680} onChange={(requested_width) => setForm({ ...form, requested_width })}/>
          <NumberField label="Yükseklik" value={form.requested_height ?? 720} min={120} max={4320} onChange={(requested_height) => setForm({ ...form, requested_height })}/>
          <NumberField label="Connection timeout (sn)" value={form.connection_timeout_seconds} min={1} max={30} step={1} onChange={(connection_timeout_seconds) => setForm({ ...form, connection_timeout_seconds })}/>
          <label className="field"><span>Reconnect backoff (sn)</span><input value={form.reconnect_schedule_seconds.join(', ')} onChange={(event) => setForm({ ...form, reconnect_schedule_seconds: parseSchedule(event.target.value) })}/><small>Artan, virgülle ayrılmış değerler.</small></label>
          <label className="toggle-row form-span"><span><strong>Kamera aktif</strong><small>MVP aynı anda bir aktif kamera çalıştırır.</small></span><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })}/></label>
        </section>
        <section className="panel">
          <div className="panel-heading"><div><p className="eyebrow">Normalize koordinatlar</p><h2>Detection Region / ROI</h2></div></div>
          <RoiEditor cameraId={selectedId} active={form.active} roi={form.roi} width={form.requested_width ?? 1280} height={form.requested_height ?? 720} onChange={(roi) => setForm({ ...form, roi })}/>
          <div className="roi-fields">
            {(['x', 'y', 'width', 'height'] as const).map((key) => <NumberField key={key} label={key.toUpperCase()} value={round(form.roi[key])} min={0} max={1} step={0.01} onChange={(value) => updateRoi(form.roi, key, value, (roi) => setForm({ ...form, roi }))}/>) }
          </div>
        </section>
        {connection && <div className={connection.connected ? 'connection-result success' : 'connection-result failure'} role="status"><strong>{connection.connected ? 'Connected' : 'Connection failed'}</strong><span>Latency: {connection.latency_ms} ms</span><span>Resolution: {connection.resolution ?? '—'}</span><span>FPS: {connection.fps?.toFixed(1) ?? '—'}</span></div>}
        <div className="camera-actions">{selectedId !== null && <button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>Sil</button>}<span/><button type="button" className="secondary-button" disabled={busy || selectedId === null} onClick={() => void testConnection()}>{busy ? 'Bekleyin…' : 'Test connection'}</button><button type="submit" className="primary-button" disabled={busy}>{busy ? 'Kaydediliyor…' : 'Kaydet'}</button></div>
      </form>
    </div>
  </>
}

function selectCamera(camera: Camera, setId: (id: number) => void, setForm: (form: CameraWrite) => void) {
  setId(camera.id)
  setForm({ name: camera.name, camera_type: 'RTSP', stream_url: camera.stream_url, username: camera.username, password: '', capture_fps_limit: camera.capture_fps_limit, detection_fps: camera.detection_fps, requested_width: camera.requested_width, requested_height: camera.requested_height, roi: camera.roi, active: camera.active, connection_timeout_seconds: camera.connection_timeout_seconds, reconnect_schedule_seconds: camera.reconnect_schedule_seconds })
}

function RuntimeDot({ state }: { state: Camera['runtime_state'] }) { return <span className={`runtime-dot runtime-${state.toLowerCase()}`} title={state}><span className="sr-only">{state}</span></span> }
function TextField({ label, value, required = false, onChange }: { label: string; value: string; required?: boolean; onChange: (value: string) => void }) { return <label className="field"><span>{label}</span><input required={required} value={value} onChange={(event) => onChange(event.target.value)}/></label> }
function NumberField({ label, value, min, max, step = 1, onChange }: { label: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void }) { return <label className="field"><span>{label}</span><input type="number" required value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))}/></label> }
function parseSchedule(value: string) { return value.split(',').map(Number).filter((item) => Number.isFinite(item) && item > 0) }
function round(value: number) { return Math.round(value * 1000) / 1000 }
function updateRoi(roi: NormalizedROI, key: keyof NormalizedROI, value: number, commit: (roi: NormalizedROI) => void) { const next = { ...roi, [key]: value }; if (next.x + next.width <= 1 && next.y + next.height <= 1 && next.width > 0 && next.height > 0) commit(next) }
