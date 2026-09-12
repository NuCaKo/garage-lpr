import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { GateConnectionResult, GateController, GateControllerWrite } from '../types'

const EMPTY_GATE: GateControllerWrite = {
  name: '',
  controller_type: 'MOCK',
  active: false,
  pulse_ms: 500,
  configuration: {},
}

export function GateControllersPage() {
  const [gates, setGates] = useState<GateController[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [form, setForm] = useState<GateControllerWrite>(EMPTY_GATE)
  const [connection, setConnection] = useState<GateConnectionResult | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    api.gateControllers(controller.signal).then((items) => {
      setGates(items)
      if (items[0]) selectGate(items[0], setSelectedId, setForm)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) showError(reason, setError, setMessage, 'Gate controller listesi alınamadı')
    })
    return () => controller.abort()
  }, [])

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setMessage(null); setError(false); setConnection(null)
    try {
      const saved = selectedId === null
        ? await api.createGateController(form)
        : await api.updateGateController(selectedId, form)
      setGates((current) => [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) => a.name.localeCompare(b.name)))
      selectGate(saved, setSelectedId, setForm)
      setMessage('Gate controller kaydedildi.')
    } catch (reason) {
      showError(reason, setError, setMessage, 'Gate controller kaydedilemedi')
    } finally { setBusy(false) }
  }

  async function testConnection() {
    if (selectedId === null) return
    setBusy(true); setMessage(null); setError(false); setConnection(null)
    try {
      setConnection(await api.testGateController(selectedId))
    } catch (reason) {
      showError(reason, setError, setMessage, 'Gate bağlantısı test edilemedi')
    } finally { setBusy(false) }
  }

  async function remove() {
    if (selectedId === null || !window.confirm('Bu gate controller ve bağlı erişim kuralları silinsin mi?')) return
    setBusy(true); setMessage(null); setError(false)
    try {
      await api.deleteGateController(selectedId)
      const remaining = gates.filter((gate) => gate.id !== selectedId)
      setGates(remaining)
      if (remaining[0]) selectGate(remaining[0], setSelectedId, setForm)
      else { setSelectedId(null); setForm(EMPTY_GATE) }
      setConnection(null)
      setMessage('Gate controller silindi.')
    } catch (reason) {
      showError(reason, setError, setMessage, 'Gate controller silinemedi')
    } finally { setBusy(false) }
  }

  const selected = gates.find((gate) => gate.id === selectedId)
  return <>
    <section className="page-heading"><div><p className="eyebrow">Phase 5 · Gate</p><h1>Gate controllers</h1><p>Kapı adaptörlerini tek güvenli komut yolu üzerinden yapılandırın. Bu fazda Mock controller zorunlu test adaptörüdür.</p></div><button type="button" className="secondary-button" onClick={() => { setSelectedId(null); setForm(EMPTY_GATE); setMessage(null); setError(false); setConnection(null) }}>Yeni controller</button></section>
    {message && <div className={error ? 'alert alert-error' : 'alert'} role={error ? 'alert' : 'status'}>{message}</div>}
    {connection && <div className={connection.connected ? 'connection-result success' : 'connection-result failure'} role="status"><span><strong>{connection.connected ? 'Connected' : 'Unavailable'}</strong></span><span>State: <strong>{connection.state}</strong></span><span>{connection.detail}</span></div>}
    <div className="gate-layout">
      <aside className="panel gate-list" aria-label="Gate controller listesi">
        <div className="panel-heading"><div><p className="eyebrow">Controllers</p><h2>Tanımlar</h2></div><span className="muted">{gates.length}</span></div>
        {gates.length === 0 && <p className="muted">Henüz gate controller eklenmedi.</p>}
        {gates.map((gate) => <button type="button" key={gate.id} className={gate.id === selectedId ? 'gate-item selected' : 'gate-item'} onClick={() => { selectGate(gate, setSelectedId, setForm); setMessage(null); setError(false); setConnection(null) }}>
          <span><strong>{gate.name}</strong><small>{gate.controller_type} · {gate.pulse_ms} ms</small></span><span className={gate.healthy ? 'runtime-dot runtime-connected' : 'runtime-dot runtime-unavailable'} aria-label={gate.healthy ? 'Sağlıklı' : 'Kullanılamıyor'}/>
        </button>)}
      </aside>
      <form className="gate-form" onSubmit={save}>
        <section className="panel form-grid">
          <div className="panel-heading form-span"><div><p className="eyebrow">Adapter</p><h2>{selected?.name ?? 'Yeni controller'}</h2></div>{selected && <span className="runtime-label"><span className={selected.healthy ? 'runtime-dot runtime-connected' : 'runtime-dot runtime-unavailable'}/>{selected.runtime_state}</span>}</div>
          <label className="field"><span>Controller adı</span><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })}/></label>
          <label className="field"><span>Controller tipi</span><select value={form.controller_type} disabled><option value="MOCK">Mock controller</option></select><small>HTTP, MQTT ve Serial adapter’lar saha gereksinimine göre eklenecek.</small></label>
          <label className="field"><span>Pulse süresi (ms)</span><input type="number" min={50} max={5000} required value={form.pulse_ms} onChange={(event) => setForm({ ...form, pulse_ms: Number(event.target.value) })}/><small>Mock OPEN durumu timer/thread oluşturmadan bu süre sonunda kapanır.</small></label>
          <label className="toggle-row"><span><strong>Controller aktif</strong><small>Pasif controller hiçbir access rule tarafından tetiklenemez.</small></span><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })}/></label>
        </section>
        <div className="gate-actions">{selectedId !== null && <button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>Sil</button>}<span/><button type="button" className="secondary-button" disabled={busy || selectedId === null || !selected?.active} onClick={() => void testConnection()}>{busy ? 'Bekleyin…' : 'Test connection'}</button><button type="submit" className="primary-button" disabled={busy}>{busy ? 'Kaydediliyor…' : 'Kaydet'}</button></div>
      </form>
    </div>
  </>
}

function selectGate(gate: GateController, setId: (id: number) => void, setForm: (form: GateControllerWrite) => void) {
  setId(gate.id)
  setForm({ name: gate.name, controller_type: gate.controller_type, active: gate.active, pulse_ms: gate.pulse_ms, configuration: {} })
}

function showError(reason: unknown, setError: (value: boolean) => void, setMessage: (value: string) => void, fallback: string) {
  setError(true)
  setMessage(reason instanceof Error ? reason.message : fallback)
}
