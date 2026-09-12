import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { RuntimeSettings } from '../types'

export function SettingsPage() {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    api.settings(controller.signal).then(setSettings).catch((error: unknown) => {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Ayarlar alınamadı')
    })
    return () => controller.abort()
  }, [])

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!settings) return
    setSaving(true)
    setMessage(null)
    try {
      setSettings(await api.saveSettings(settings))
      setMessage('Ayarlar yerel veritabanına kaydedildi.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Kaydetme başarısız')
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return <div className="panel" aria-busy="true">Ayarlar yükleniyor…</div>

  return <>
    <section className="page-heading"><div><p className="eyebrow">Merkezi yapılandırma</p><h1>Sistem ayarları</h1><p>Güvenli runtime varsayılanları restart sonrasında korunur.</p></div></section>
    {message && <div className="alert" role="status">{message}</div>}
    <form className="settings-form" onSubmit={save}>
      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">Emniyet sınırı</p><h2>Çalışma modu</h2></div></div>
        <label className="toggle-row"><span><strong>Simulation mode</strong><small>Gerçek gate controller'a komut gitmez.</small></span><input type="checkbox" checked={settings.simulation_mode} onChange={(e) => setSettings({ ...settings, simulation_mode: e.target.checked })}/></label>
        <label className="toggle-row"><span><strong>Maintenance mode</strong><small>Otomatik erişim kararları kapalı tutulur.</small></span><input type="checkbox" checked={settings.maintenance_mode} onChange={(e) => setSettings({ ...settings, maintenance_mode: e.target.checked })}/></label>
      </section>
      <section className="panel form-grid">
        <div className="panel-heading form-span"><div><p className="eyebrow">Kaynak bütçesi</p><h2>Recognition ayarları</h2></div></div>
        <NumberField label="Global Detection FPS tavanı" value={settings.detection_fps} min={0.5} max={15} step={0.5} onChange={(value) => setSettings({ ...settings, detection_fps: value })}/>
        <NumberField label="Minimum güven" value={settings.recognition_min_confidence} min={0} max={1} step={0.01} onChange={(value) => setSettings({ ...settings, recognition_min_confidence: value })}/>
        <NumberField label="Gerekli doğrulama" value={settings.required_confirmations} min={2} max={10} onChange={(value) => setSettings({ ...settings, required_confirmations: value })}/>
        <NumberField label="Doğrulama penceresi (ms)" value={settings.confirmation_window_ms} min={250} max={10000} step={250} onChange={(value) => setSettings({ ...settings, confirmation_window_ms: value })}/>
        <NumberField label="Tracking IoU eşiği" value={settings.tracking_iou_threshold} min={0.05} max={0.95} step={0.05} onChange={(tracking_iou_threshold) => setSettings({ ...settings, tracking_iou_threshold })}/>
        <NumberField label="Track idle süresi (ms)" value={settings.tracking_max_idle_ms} min={250} max={10000} step={250} onChange={(tracking_max_idle_ms) => setSettings({ ...settings, tracking_max_idle_ms })}/>
        <NumberField label="Maksimum aktif track" value={settings.max_active_tracks} min={10} max={2048} onChange={(max_active_tracks) => setSettings({ ...settings, max_active_tracks })}/>
        <NumberField label="Plaka cooldown (sn)" value={settings.gate_cooldown_seconds} min={1} max={3600} onChange={(value) => setSettings({ ...settings, gate_cooldown_seconds: value })}/>
        <NumberField label="Global cooldown (sn)" value={settings.global_gate_cooldown_seconds} min={1} max={3600} onChange={(global_gate_cooldown_seconds) => setSettings({ ...settings, global_gate_cooldown_seconds })}/>
        <NumberField label="Gate komut timeout (sn)" value={settings.gate_command_timeout_seconds} min={0.1} max={30} step={0.1} onChange={(gate_command_timeout_seconds) => setSettings({ ...settings, gate_command_timeout_seconds })}/>
        <TextField label="Yerel saat dilimi" value={settings.local_timezone} onChange={(local_timezone) => setSettings({ ...settings, local_timezone })}/>
        <NumberField label="Dashboard polling (sn)" value={settings.metrics_poll_interval_seconds} min={5} max={300} onChange={(value) => setSettings({ ...settings, metrics_poll_interval_seconds: value })}/>
        <NumberField label="Plate event minimum aralığı (sn)" value={settings.plate_detection_event_interval_seconds} min={1} max={300} onChange={(plate_detection_event_interval_seconds) => setSettings({ ...settings, plate_detection_event_interval_seconds })}/>
      </section>
      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">Disk kontrolü</p><h2>Event snapshotları</h2></div></div>
        <label className="toggle-row"><span><strong>Snapshot kaydet</strong><small>Yalnızca erişim kararları ve recognition hatalarında JPEG oluşturur.</small></span><input type="checkbox" checked={settings.snapshot_enabled} onChange={(event) => setSettings({ ...settings, snapshot_enabled: event.target.checked })}/></label>
        <NumberField label="Snapshot retention (gün)" value={settings.snapshot_retention_days} min={1} max={3650} onChange={(snapshot_retention_days) => setSettings({ ...settings, snapshot_retention_days })}/>
        <NumberField label="Event retention (gün)" value={settings.event_retention_days} min={1} max={3650} onChange={(event_retention_days) => setSettings({ ...settings, event_retention_days })}/>
      </section>
      <section className="panel form-grid">
        <div className="panel-heading form-span"><div><p className="eyebrow">ONNX Runtime</p><h2>Detector ve OCR modelleri</h2></div><span className="muted">Model dosyaları yerel olmalıdır</span></div>
        <label className="field"><span>Execution provider</span><select value={settings.inference_provider} onChange={(event) => setSettings({ ...settings, inference_provider: event.target.value as RuntimeSettings['inference_provider'] })}><option value="auto">Auto · CUDA → CPU</option><option value="cpu">CPU</option><option value="cuda">CUDA zorunlu</option></select></label>
        <label className="field"><span>Detector output</span><select value={settings.detector_output_format} onChange={(event) => setSettings({ ...settings, detector_output_format: event.target.value as RuntimeSettings['detector_output_format'] })}><option value="xyxy">XYXY · N×6</option><option value="yolo_v8">YOLOv8 · channels×N</option></select></label>
        <TextField label="Detector model yolu" value={settings.detector_model_path} onChange={(detector_model_path) => setSettings({ ...settings, detector_model_path })}/>
        <TextField label="OCR model yolu" value={settings.ocr_model_path} onChange={(ocr_model_path) => setSettings({ ...settings, ocr_model_path })}/>
        <NumberField label="Detector input genişliği" value={settings.detector_input_width} min={160} max={1280} step={32} onChange={(detector_input_width) => setSettings({ ...settings, detector_input_width })}/>
        <NumberField label="Detector input yüksekliği" value={settings.detector_input_height} min={160} max={1280} step={32} onChange={(detector_input_height) => setSettings({ ...settings, detector_input_height })}/>
        <NumberField label="Detection confidence" value={settings.detector_confidence_threshold} min={0.1} max={1} step={0.01} onChange={(detector_confidence_threshold) => setSettings({ ...settings, detector_confidence_threshold })}/>
        <NumberField label="NMS IoU threshold" value={settings.detector_iou_threshold} min={0.1} max={0.9} step={0.01} onChange={(detector_iou_threshold) => setSettings({ ...settings, detector_iou_threshold })}/>
        <NumberField label="Frame başına maksimum plaka" value={settings.max_plates_per_frame} min={1} max={10} onChange={(max_plates_per_frame) => setSettings({ ...settings, max_plates_per_frame })}/>
        <label className="field"><span>OCR kanalları</span><select value={settings.ocr_input_channels} onChange={(event) => setSettings({ ...settings, ocr_input_channels: Number(event.target.value) as 1 | 3 })}><option value={1}>1 · Grayscale</option><option value={3}>3 · RGB</option></select></label>
        <NumberField label="OCR input genişliği" value={settings.ocr_input_width} min={64} max={512} onChange={(ocr_input_width) => setSettings({ ...settings, ocr_input_width })}/>
        <NumberField label="OCR input yüksekliği" value={settings.ocr_input_height} min={16} max={128} onChange={(ocr_input_height) => setSettings({ ...settings, ocr_input_height })}/>
        <label className="field form-span"><span>OCR charset</span><input value={settings.ocr_charset} onChange={(event) => setSettings({ ...settings, ocr_charset: event.target.value.toUpperCase() })}/><small>CTC blank sınıfı indeks 0; charset sınıfları indeks 1'den başlar.</small></label>
      </section>
      <div className="form-actions"><button className="primary-button" disabled={saving} type="submit">{saving ? 'Kaydediliyor…' : 'Ayarları kaydet'}</button></div>
    </form>
  </>
}

function NumberField({ label, value, min, max, step = 1, onChange }: { label: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void }) {
  return <label className="field"><span>{label}</span><input type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))}/></label>
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="field"><span>{label}</span><input required value={value} onChange={(event) => onChange(event.target.value)}/></label>
}
