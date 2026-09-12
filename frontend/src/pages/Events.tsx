import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { OperationalEvent } from '../types'

const PAGE_SIZE = 50
const RECONNECT_DELAYS_MS = [1_000, 2_000, 5_000, 10_000, 30_000]
const eventTypes = [
  'camera_connected', 'camera_disconnected', 'plate_detected', 'plate_recognized',
  'recognition_error', 'access_granted', 'access_denied', 'gate_open_requested',
  'gate_open_success', 'gate_open_failed', 'simulated_gate_open', 'system_started',
  'system_stopped',
]

export function EventsPage() {
  const [events, setEvents] = useState<OperationalEvent[]>([])
  const [eventType, setEventType] = useState('')
  const [plate, setPlate] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [liveState, setLiveState] = useState('Canlı bağlantı kuruluyor')
  const activeFilters = useRef({ eventType: '', plate: '', status: '' })
  const liveView = useRef({ offset: 0, filtered: false })

  const load = useCallback(async (nextOffset: number, signal?: AbortSignal) => {
    setLoading(true)
    const filters = activeFilters.current
    const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(nextOffset) })
    if (filters.eventType) query.set('event_type', filters.eventType)
    if (filters.plate) query.set('plate', filters.plate)
    if (filters.status) query.set('status', filters.status)
    try {
      const page = await api.events(query.toString(), signal)
      setEvents(page.items)
      setTotal(page.total)
      setOffset(page.offset)
      setError(null)
    } catch (reason) {
      if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Olaylar alınamadı')
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => void load(0, controller.signal), 0)
    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [load])

  useEffect(() => {
    liveView.current.offset = offset
  }, [offset])

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: number | null = null
    let disposed = false
    let attempt = 0
    const connect = () => {
      if (disposed) return
      socket = new WebSocket(api.eventSocketUrl())
      socket.onopen = () => {
        attempt = 0
        setLiveState('Canlı event akışı bağlı')
      }
      socket.onmessage = (message) => {
        let payload: Partial<OperationalEvent> & { type?: string }
        try {
          payload = JSON.parse(String(message.data)) as Partial<OperationalEvent> & { type?: string }
        } catch {
          return
        }
        if (payload.type === 'heartbeat' || !payload.event_id || !payload.event_type) return
        setLiveState(`Yeni olay: ${eventLabel(payload.event_type)}`)
        if (liveView.current.offset === 0 && !liveView.current.filtered) {
          setEvents((current) => [payload as OperationalEvent, ...current.filter((item) => item.event_id !== payload.event_id)].slice(0, PAGE_SIZE))
          setTotal((current) => current + 1)
        }
      }
      socket.onclose = () => {
        if (disposed) return
        const delay = RECONNECT_DELAYS_MS[Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)] ?? 30_000
        attempt += 1
        setLiveState(`Canlı bağlantı kesildi · ${delay / 1000} sn sonra tekrar denenecek`)
        reconnectTimer = window.setTimeout(connect, delay)
      }
      socket.onerror = () => socket?.close()
    }
    connect()
    return () => {
      disposed = true
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [])

  function applyFilters(event: FormEvent) {
    event.preventDefault()
    activeFilters.current = {
      eventType,
      plate: plate.trim().toUpperCase(),
      status: status.trim(),
    }
    liveView.current.filtered = Boolean(eventType || plate.trim() || status.trim())
    void load(0)
  }

  function clearFilters() {
    setEventType('')
    setPlate('')
    setStatus('')
    activeFilters.current = { eventType: '', plate: '', status: '' }
    liveView.current.filtered = false
    void load(0)
  }

  return <>
    <section className="page-heading">
      <div><p className="eyebrow">Kalıcı denetim izi</p><h1>Olaylar</h1><p>Recognition, erişim, kamera ve gate sonuçları SQLite üzerinde saklanır.</p></div>
      <span className="live-state" role="status" aria-atomic="true"><span aria-hidden="true" />{liveState}</span>
    </section>
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    <form className="panel event-filters" onSubmit={applyFilters}>
      <label className="field"><span>Olay tipi</span><select value={eventType} onChange={(event) => setEventType(event.target.value)}><option value="">Tümü</option>{eventTypes.map((item) => <option key={item} value={item}>{eventLabel(item)}</option>)}</select></label>
      <label className="field"><span>Plaka</span><input value={plate} maxLength={24} onChange={(event) => setPlate(event.target.value)} placeholder="34ABC123" /></label>
      <label className="field"><span>Durum</span><input value={status} maxLength={64} onChange={(event) => setStatus(event.target.value)} placeholder="AUTHORIZED" /></label>
      <div className="event-filter-actions"><button className="secondary-button" type="button" onClick={clearFilters}>Temizle</button><button className="primary-button" type="submit">Filtrele</button></div>
    </form>
    <section className="panel event-panel" aria-busy={loading}>
      <div className="panel-heading"><div><p className="eyebrow">Sonuçlar</p><h2>{total} kayıt</h2></div><span className="muted">Sayfa {Math.floor(offset / PAGE_SIZE) + 1}</span></div>
      <div className="event-table-wrap">
        <table className="event-table">
          <caption className="sr-only">Sistem olaylarının tarih sırasına göre listesi</caption>
          <thead><tr><th>Zaman</th><th>Olay</th><th>Plaka</th><th>Durum</th><th>Kaynak</th><th>Detay</th></tr></thead>
          <tbody>{events.map((item) => <EventRow key={item.event_id} event={item} />)}</tbody>
        </table>
        {!loading && events.length === 0 && <p className="event-empty">Filtrelerle eşleşen olay bulunamadı.</p>}
      </div>
      <div className="pagination"><button className="secondary-button" type="button" disabled={offset === 0 || loading} onClick={() => void load(Math.max(0, offset - PAGE_SIZE))}>Daha yeni</button><button className="secondary-button" type="button" disabled={offset + PAGE_SIZE >= total || loading} onClick={() => void load(offset + PAGE_SIZE)}>Daha eski</button></div>
    </section>
  </>
}

function EventRow({ event }: { event: OperationalEvent }) {
  return <tr>
    <td><time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleString('tr-TR')}</time></td>
    <td><span className={`event-kind event-${eventTone(event.event_type)}`}>{eventLabel(event.event_type)}</span></td>
    <td className="plate-cell">{event.plate ?? '—'}</td>
    <td>{event.status}</td>
    <td>{event.camera_id ? `Kamera ${event.camera_id}` : event.gate_controller_id ? `Gate ${event.gate_controller_id}` : 'Sistem'}</td>
    <td>{event.reason || Object.keys(event.metadata).length > 0 ? <details><summary>Görüntüle</summary><pre>{JSON.stringify({ reason: event.reason, ...event.metadata }, null, 2)}</pre></details> : '—'}</td>
  </tr>
}

function eventLabel(value: string) {
  return value.split('_').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
}

function eventTone(value: string) {
  if (value.includes('failed') || value.includes('denied') || value.includes('error') || value.includes('disconnected')) return 'bad'
  if (value.includes('success') || value.includes('granted') || value.includes('connected')) return 'good'
  return 'neutral'
}
