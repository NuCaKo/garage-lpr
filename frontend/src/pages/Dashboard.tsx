import type { InferenceMetrics, ResourceMetrics, SystemHealth } from '../types'
import { StatusBadge } from '../components/StatusBadge'

const pipeline = ['Kamera', 'Örnekleme', 'Algılama', 'OCR', 'Doğrulama', 'Yetki', 'Kapı']

export function Dashboard({ health, inference, resources, loading, error }: { health: SystemHealth | null; inference: InferenceMetrics | null; resources: ResourceMetrics | null; loading: boolean; error: string | null }) {
  return <>
    <section className="page-heading">
      <div><p className="eyebrow">Operasyon görünümü</p><h1>Dashboard</h1><p>Sistemin temel bileşenleri ve fail-safe çalışma durumu.</p></div>
      {health && <StatusBadge state={health.state} />}
    </section>

    {error && <div className="alert alert-error" role="alert">{error}</div>}
    <section className="metric-grid" aria-busy={loading}>
      {['camera', 'database', 'detector', 'gate'].map((name) => {
        const component = health?.components[name]
        const titles: Record<string, string> = { camera: 'Kamera', database: 'Veritabanı', detector: 'Algılama', gate: 'Kapı' }
        return <article className="metric-card" key={name}>
          <div className="metric-header"><span>{titles[name]}</span>{component && <StatusBadge state={component.state} />}</div>
          <strong>{component ? component.detail : 'Durum okunuyor…'}</strong>
          <small>{name === 'database' ? 'SQLite + WAL' : name === 'detector' ? (inference?.detector_provider ?? 'Model bekleniyor') : 'Fail-safe status'}</small>
        </article>
      })}
    </section>

    <section className="panel">
      <div className="panel-heading"><div><p className="eyebrow">Recognition pipeline</p><h2>İşleme hattı</h2></div><span className="muted" role="status" aria-atomic="true">{inference?.detail ?? 'Durum okunuyor'}</span></div>
      <ol className="pipeline" aria-label="Plaka tanıma işleme hattı">
        {pipeline.map((step, index) => <li key={step}><span>{String(index + 1).padStart(2, '0')}</span>{step}</li>)}
      </ol>
    </section>

    <section className="metric-grid inference-metrics" aria-label="Inference performans metrikleri">
      <Metric label="Detection FPS" value={formatMetric(inference?.effective_detection_fps, ' fps')} detail={`Global tavan · buffer ${inference?.frame_buffer_capacity ?? 1}`}/>
      <Metric label="Detector latency" value={formatMetric(inference?.detection_latency_ms, ' ms')} detail={`${inference?.plates_detected ?? 0} detection`}/>
      <Metric label="OCR latency" value={formatMetric(inference?.ocr_latency_ms, ' ms')} detail={`${inference?.ocr_calls ?? 0} crop OCR`}/>
      <Metric label="Tracking" value={String(inference?.active_tracks ?? 0)} detail={`${inference?.pending_validations ?? 0} temporal doğrulama bekliyor`}/>
    </section>

    <section className="metric-grid inference-metrics" aria-label="Sistem kaynak metrikleri">
      <Metric label="System CPU" value={`${resources?.system_cpu_percent.toFixed(1) ?? '0.0'}%`} detail={`Process ${resources?.process_cpu_percent.toFixed(1) ?? '0.0'}%`}/>
      <Metric label="System RAM" value={`${resources?.system_ram_percent.toFixed(1) ?? '0.0'}%`} detail="İşletim sistemi kullanımı"/>
      <Metric label="Process RAM" value={formatBytes(resources?.process_rss_bytes)} detail={`${resources?.process_thread_count ?? 0} thread`}/>
      <Metric label="Disk free" value={formatBytes(resources?.disk_free_bytes)} detail={`${resources?.disk_percent.toFixed(1) ?? '0.0'}% kullanım`}/>
    </section>

    <section className="split-grid">
      <article className="panel empty-state"><p className="eyebrow">Son doğrulanan plaka</p><strong>{inference?.last_decision_plate ?? '—'}</strong><p>{inference?.recognized_plates ?? 0} temporal karar · son yetki: {inference?.last_authorization_status ?? '—'}.</p></article>
      <article className="panel empty-state"><p className="eyebrow">Son erişim kararı</p><strong>{inference?.last_recognition_outcome ?? 'Güvenli bekleme'}</strong><p>{inference?.access_ready ?? 0} gate için uygun · {inference?.access_denied ?? 0} reddedildi · {inference?.cooldown_suppressed ?? 0} cooldown.</p></article>
      <article className="panel empty-state"><p className="eyebrow">Son gate sonucu</p><strong>{inference?.last_gate_outcome ?? 'Komut yok'}</strong><p>{inference?.gate_open_success ?? 0} başarılı · {inference?.simulated_gate_open ?? 0} simülasyon · {inference?.gate_open_failed ?? 0} engelli/hatalı.</p></article>
    </section>
  </>
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="metric-card compact-metric"><div className="metric-header"><span>{label}</span></div><strong>{value}</strong><small>{detail}</small></article>
}

function formatMetric(value: number | undefined, unit: string) {
  return `${(value ?? 0).toFixed(2)}${unit}`
}

function formatBytes(value = 0) {
  if (value <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** index).toFixed(index > 1 ? 1 : 0)} ${units[index]}`
}
