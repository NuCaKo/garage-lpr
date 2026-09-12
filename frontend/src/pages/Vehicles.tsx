import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { Vehicle, VehicleWrite } from '../types'

const DAYS = [
  ['Pzt', 0], ['Sal', 1], ['Çar', 2], ['Per', 3],
  ['Cum', 4], ['Cmt', 5], ['Paz', 6],
] as const

const EMPTY_VEHICLE: VehicleWrite = {
  plate: '', owner: '', description: null, active: true,
  valid_from: null, valid_until: null, allowed_days: [0, 1, 2, 3, 4, 5, 6],
  allowed_start_time: null, allowed_end_time: null, notes: null,
}

export function VehiclesPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [form, setForm] = useState<VehicleWrite>(EMPTY_VEHICLE)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    api.vehicles(controller.signal).then((items) => {
      setVehicles(items)
      if (items[0]) selectVehicle(items[0], setSelectedId, setForm)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        setError(true)
        setMessage(reason instanceof Error ? reason.message : 'Araçlar alınamadı')
      }
    })
    return () => controller.abort()
  }, [])

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setMessage(null); setError(false)
    try {
      const payload = cleanPayload(form)
      const saved = selectedId === null
        ? await api.createVehicle(payload)
        : await api.updateVehicle(selectedId, payload)
      setVehicles((current) => [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) => a.plate.localeCompare(b.plate)))
      selectVehicle(saved, setSelectedId, setForm)
      setMessage('Yetkili araç kaydedildi.')
    } catch (reason) {
      setError(true)
      setMessage(reason instanceof Error ? reason.message : 'Araç kaydedilemedi')
    } finally { setBusy(false) }
  }

  async function remove() {
    if (selectedId === null || !window.confirm('Bu yetkili araç silinsin mi?')) return
    setBusy(true); setMessage(null); setError(false)
    try {
      await api.deleteVehicle(selectedId)
      const remaining = vehicles.filter((vehicle) => vehicle.id !== selectedId)
      setVehicles(remaining)
      if (remaining[0]) selectVehicle(remaining[0], setSelectedId, setForm)
      else { setSelectedId(null); setForm(EMPTY_VEHICLE) }
      setMessage('Yetkili araç silindi.')
    } catch (reason) {
      setError(true)
      setMessage(reason instanceof Error ? reason.message : 'Araç silinemedi')
    } finally { setBusy(false) }
  }

  const selected = vehicles.find((vehicle) => vehicle.id === selectedId)
  return <>
    <section className="page-heading"><div><p className="eyebrow">Phase 4 · Authorization</p><h1>Yetkili araçlar</h1><p>Plaka geçerliliğini, haftalık erişim günlerini ve saat aralığını yerel olarak yönetin.</p></div><button type="button" className="secondary-button" onClick={() => { setSelectedId(null); setForm(EMPTY_VEHICLE); setMessage(null); setError(false) }}>Yeni araç</button></section>
    {message && <div className={error ? 'alert alert-error' : 'alert'} role={error ? 'alert' : 'status'}>{message}</div>}
    <div className="vehicle-layout">
      <aside className="panel vehicle-list" aria-label="Yetkili araç listesi">
        <div className="panel-heading"><div><p className="eyebrow">Kayıtlar</p><h2>Araçlar</h2></div><span className="muted">{vehicles.length}</span></div>
        {vehicles.length === 0 && <p className="muted">Henüz yetkili araç eklenmedi.</p>}
        {vehicles.map((vehicle) => <button type="button" key={vehicle.id} className={vehicle.id === selectedId ? 'vehicle-item selected' : 'vehicle-item'} onClick={() => { selectVehicle(vehicle, setSelectedId, setForm); setMessage(null); setError(false) }}>
          <span><strong>{vehicle.plate}</strong><small>{vehicle.owner}</small></span><span className={vehicle.active ? 'access-state active' : 'access-state'}>{vehicle.active ? 'Aktif' : 'Pasif'}</span>
        </button>)}
      </aside>
      <form className="vehicle-form" onSubmit={save}>
        <section className="panel form-grid">
          <div className="panel-heading form-span"><div><p className="eyebrow">Kimlik</p><h2>{selected?.plate ?? 'Yeni yetkili araç'}</h2></div></div>
          <label className="field"><span>Plaka</span><input required autoCapitalize="characters" value={form.plate} placeholder="34ABC123" onChange={(event) => setForm({ ...form, plate: event.target.value.toUpperCase() })}/><small>Boşluk ve tire kayıtta normalize edilir.</small></label>
          <label className="field"><span>Araç sahibi</span><input required value={form.owner} onChange={(event) => setForm({ ...form, owner: event.target.value })}/></label>
          <label className="field form-span"><span>Açıklama</span><input value={form.description ?? ''} onChange={(event) => setForm({ ...form, description: event.target.value })}/></label>
          <label className="toggle-row form-span"><span><strong>Araç aktif</strong><small>Pasif araç her koşulda `DISABLED` sonucu üretir.</small></span><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })}/></label>
        </section>
        <section className="panel form-grid">
          <div className="panel-heading form-span"><div><p className="eyebrow">Erişim penceresi</p><h2>Tarih ve saat kuralları</h2></div></div>
          <label className="field"><span>Başlangıç tarihi</span><input type="date" value={form.valid_from ?? ''} onChange={(event) => setForm({ ...form, valid_from: event.target.value || null })}/></label>
          <label className="field"><span>Bitiş tarihi</span><input type="date" value={form.valid_until ?? ''} onChange={(event) => setForm({ ...form, valid_until: event.target.value || null })}/></label>
          <fieldset className="day-selector form-span"><legend>İzin verilen günler</legend><div>{DAYS.map(([label, day]) => <label key={day}><input type="checkbox" checked={form.allowed_days.includes(day)} onChange={() => setForm({ ...form, allowed_days: toggleDay(form.allowed_days, day) })}/><span>{label}</span></label>)}</div></fieldset>
          <label className="field"><span>Başlangıç saati</span><input type="time" value={shortTime(form.allowed_start_time)} onChange={(event) => setForm({ ...form, allowed_start_time: event.target.value || null, allowed_end_time: event.target.value ? (form.allowed_end_time ?? '23:59') : null })}/></label>
          <label className="field"><span>Bitiş saati</span><input type="time" value={shortTime(form.allowed_end_time)} onChange={(event) => setForm({ ...form, allowed_end_time: event.target.value || null, allowed_start_time: event.target.value ? (form.allowed_start_time ?? '00:00') : null })}/><small>Gece yarısını aşan aralıklar desteklenir.</small></label>
          <label className="field form-span"><span>Notlar</span><textarea rows={3} value={form.notes ?? ''} onChange={(event) => setForm({ ...form, notes: event.target.value })}/></label>
        </section>
        <div className="vehicle-actions">{selectedId !== null && <button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>Sil</button>}<span/><button type="submit" className="primary-button" disabled={busy}>{busy ? 'Kaydediliyor…' : 'Aracı kaydet'}</button></div>
      </form>
    </div>
  </>
}

function selectVehicle(vehicle: Vehicle, setId: (id: number) => void, setForm: (form: VehicleWrite) => void) {
  setId(vehicle.id)
  setForm({ plate: vehicle.plate, owner: vehicle.owner, description: vehicle.description, active: vehicle.active, valid_from: vehicle.valid_from, valid_until: vehicle.valid_until, allowed_days: vehicle.allowed_days, allowed_start_time: vehicle.allowed_start_time, allowed_end_time: vehicle.allowed_end_time, notes: vehicle.notes })
}

function cleanPayload(form: VehicleWrite): VehicleWrite {
  return { ...form, description: form.description?.trim() || null, notes: form.notes?.trim() || null }
}

function toggleDay(days: number[], day: number) {
  return days.includes(day) ? days.filter((item) => item !== day) : [...days, day].sort()
}

function shortTime(value: string | null) { return value?.slice(0, 5) ?? '' }
