import { StatusBadge } from '../components/StatusBadge'
import type { ResourceMetrics, SystemHealth } from '../types'

export function SystemHealthPage({ health, resources, loading, error }: { health: SystemHealth | null; resources: ResourceMetrics | null; loading: boolean; error: string | null }) {
  return <>
    <section className="page-heading"><div><p className="eyebrow">Operational readiness</p><h1>Sistem sağlığı</h1><p>Servis durumları ve işletim sistemi kaynakları düşük frekansta örneklenir.</p></div>{health && <StatusBadge state={health.state} />}</section>
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    <section className="resource-grid" aria-busy={loading}>
      <Resource label="Sistem CPU" value={`${resources?.system_cpu_percent.toFixed(1) ?? '0.0'}%`} detail={`Process ${resources?.process_cpu_percent.toFixed(1) ?? '0.0'}%`} />
      <Resource label="Sistem RAM" value={`${resources?.system_ram_percent.toFixed(1) ?? '0.0'}%`} detail={`${formatBytes(resources?.system_ram_used_bytes)} / ${formatBytes(resources?.system_ram_total_bytes)}`} />
      <Resource label="Process RAM" value={formatBytes(resources?.process_rss_bytes)} detail={`${resources?.process_thread_count ?? 0} thread`} />
      <Resource label="Disk" value={`${resources?.disk_percent.toFixed(1) ?? '0.0'}%`} detail={`${formatBytes(resources?.disk_free_bytes)} boş`} />
    </section>
    <section className="panel health-panel">
      <div className="panel-heading"><div><p className="eyebrow">Bileşenler</p><h2>Servis health</h2></div><span className="muted">Uptime {formatDuration(resources?.uptime_seconds)}</span></div>
      <div className="health-list">{Object.entries(health?.components ?? {}).map(([name, component]) => <article key={name}><div><strong>{componentLabel(name)}</strong><p>{component.detail}</p></div><StatusBadge state={component.state} /></article>)}</div>
    </section>
  </>
}

function Resource({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="metric-card compact-metric"><div className="metric-header"><span>{label}</span></div><strong>{value}</strong><small>{detail}</small></article>
}

function formatBytes(value = 0) {
  if (value <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** index).toFixed(index > 1 ? 1 : 0)} ${units[index]}`
}

function formatDuration(value = 0) {
  if (value < 60) return `${Math.floor(value)} sn`
  if (value < 3600) return `${Math.floor(value / 60)} dk`
  return `${(value / 3600).toFixed(1)} sa`
}

function componentLabel(value: string) {
  const labels: Record<string, string> = { api: 'API', database: 'Veritabanı', camera: 'Kamera', detector: 'Detector', ocr: 'OCR', gate: 'Gate', events: 'Event audit', storage: 'Snapshot storage' }
  return labels[value] ?? value
}
