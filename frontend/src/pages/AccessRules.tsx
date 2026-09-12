import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { AccessRule, AccessRuleWrite, Camera, GateController, Vehicle } from '../types'

const EMPTY_RULE: AccessRuleWrite = {
  name: '', vehicle_id: 0, camera_id: null, gate_controller_id: 0, active: true,
}

export function AccessRulesPage() {
  const [rules, setRules] = useState<AccessRule[]>([])
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [cameras, setCameras] = useState<Camera[]>([])
  const [gates, setGates] = useState<GateController[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [form, setForm] = useState<AccessRuleWrite>(EMPTY_RULE)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([api.accessRules(controller.signal), api.vehicles(controller.signal), api.cameras(controller.signal), api.gateControllers(controller.signal)]).then(([nextRules, nextVehicles, nextCameras, nextGates]) => {
      setRules(nextRules); setVehicles(nextVehicles); setCameras(nextCameras); setGates(nextGates)
      if (nextRules[0]) selectRule(nextRules[0], setSelectedId, setForm)
      else setForm(newRule(nextVehicles, nextCameras, nextGates))
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) { setError(true); setMessage(reason instanceof Error ? reason.message : 'Erişim kuralları alınamadı') }
    })
    return () => controller.abort()
  }, [])

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setMessage(null); setError(false)
    try {
      const saved = selectedId === null ? await api.createAccessRule(form) : await api.updateAccessRule(selectedId, form)
      setRules((current) => [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) => a.name.localeCompare(b.name)))
      selectRule(saved, setSelectedId, setForm)
      setMessage('Erişim kuralı kaydedildi.')
    } catch (reason) {
      setError(true); setMessage(reason instanceof Error ? reason.message : 'Erişim kuralı kaydedilemedi')
    } finally { setBusy(false) }
  }

  async function remove() {
    if (selectedId === null || !window.confirm('Bu erişim kuralı silinsin mi?')) return
    setBusy(true); setMessage(null); setError(false)
    try {
      await api.deleteAccessRule(selectedId)
      const remaining = rules.filter((rule) => rule.id !== selectedId)
      setRules(remaining)
      if (remaining[0]) selectRule(remaining[0], setSelectedId, setForm)
      else { setSelectedId(null); setForm(newRule(vehicles, cameras, gates)) }
      setMessage('Erişim kuralı silindi.')
    } catch (reason) {
      setError(true); setMessage(reason instanceof Error ? reason.message : 'Erişim kuralı silinemedi')
    } finally { setBusy(false) }
  }

  const selected = rules.find((rule) => rule.id === selectedId)
  const prerequisitesReady = vehicles.length > 0 && gates.length > 0
  return <>
    <section className="page-heading"><div><p className="eyebrow">Phase 5 · Routing</p><h1>Erişim kuralları</h1><p>Doğrulanmış aracı, görüntünün geldiği kamera üzerinden tek bir gate controller’a bağlayın.</p></div><button type="button" className="secondary-button" disabled={!prerequisitesReady} onClick={() => { setSelectedId(null); setForm(newRule(vehicles, cameras, gates)); setMessage(null); setError(false) }}>Yeni kural</button></section>
    {!prerequisitesReady && <div className="alert alert-error" role="alert">Kural oluşturmadan önce en az bir araç ve gate controller tanımlayın.</div>}
    {message && <div className={error ? 'alert alert-error' : 'alert'} role={error ? 'alert' : 'status'}>{message}</div>}
    <div className="rule-layout">
      <aside className="panel rule-list" aria-label="Erişim kuralı listesi">
        <div className="panel-heading"><div><p className="eyebrow">Routing</p><h2>Kurallar</h2></div><span className="muted">{rules.length}</span></div>
        {rules.length === 0 && <p className="muted">Henüz erişim kuralı eklenmedi.</p>}
        {rules.map((rule) => <button type="button" key={rule.id} className={rule.id === selectedId ? 'rule-item selected' : 'rule-item'} onClick={() => { selectRule(rule, setSelectedId, setForm); setMessage(null); setError(false) }}><span><strong>{rule.name}</strong><small>{vehicleLabel(rule.vehicle_id, vehicles)} → {gateLabel(rule.gate_controller_id, gates)}</small></span><span className={rule.active ? 'access-state active' : 'access-state'}>{rule.active ? 'Aktif' : 'Pasif'}</span></button>)}
      </aside>
      <form className="rule-form" onSubmit={save}>
        <section className="panel form-grid">
          <div className="panel-heading form-span"><div><p className="eyebrow">Karar rotası</p><h2>{selected?.name ?? 'Yeni erişim kuralı'}</h2></div></div>
          <label className="field form-span"><span>Kural adı</span><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })}/></label>
          <label className="field"><span>Yetkili araç</span><select required value={form.vehicle_id || ''} onChange={(event) => setForm({ ...form, vehicle_id: Number(event.target.value) })}><option value="" disabled>Araç seçin</option>{vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.plate} · {vehicle.owner}</option>)}</select></label>
          <label className="field"><span>Kamera</span><select value={form.camera_id ?? ''} onChange={(event) => setForm({ ...form, camera_id: event.target.value ? Number(event.target.value) : null })}><option value="">Tüm kameralar (fallback)</option>{cameras.map((camera) => <option key={camera.id} value={camera.id}>{camera.name}</option>)}</select><small>Kameraya özel kural, fallback kuralından önce değerlendirilir.</small></label>
          <label className="field form-span"><span>Gate controller</span><select required value={form.gate_controller_id || ''} onChange={(event) => setForm({ ...form, gate_controller_id: Number(event.target.value) })}><option value="" disabled>Controller seçin</option>{gates.map((gate) => <option key={gate.id} value={gate.id}>{gate.name} · {gate.active ? gate.runtime_state : 'Pasif'}</option>)}</select></label>
          <label className="toggle-row form-span"><span><strong>Kural aktif</strong><small>Pasif kurallar gate orchestration tarafından tamamen yok sayılır.</small></span><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })}/></label>
        </section>
        <div className="rule-actions">{selectedId !== null && <button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>Sil</button>}<span/><button type="submit" className="primary-button" disabled={busy || !prerequisitesReady}>{busy ? 'Kaydediliyor…' : 'Kuralı kaydet'}</button></div>
      </form>
    </div>
  </>
}

function newRule(vehicles: Vehicle[], cameras: Camera[], gates: GateController[]): AccessRuleWrite {
  return { ...EMPTY_RULE, vehicle_id: vehicles[0]?.id ?? 0, camera_id: cameras[0]?.id ?? null, gate_controller_id: gates[0]?.id ?? 0 }
}

function selectRule(rule: AccessRule, setId: (id: number) => void, setForm: (form: AccessRuleWrite) => void) {
  setId(rule.id)
  setForm({ name: rule.name, vehicle_id: rule.vehicle_id, camera_id: rule.camera_id, gate_controller_id: rule.gate_controller_id, active: rule.active })
}

function vehicleLabel(id: number, vehicles: Vehicle[]) { return vehicles.find((vehicle) => vehicle.id === id)?.plate ?? `Araç #${id}` }
function gateLabel(id: number, gates: GateController[]) { return gates.find((gate) => gate.id === id)?.name ?? `Gate #${id}` }
