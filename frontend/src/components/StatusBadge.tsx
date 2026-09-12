import type { HealthState } from '../types'

export function StatusBadge({ state }: { state: HealthState }) {
  const label = state === 'HEALTHY' ? 'Sağlıklı' : state === 'DEGRADED' ? 'Sınırlı' : 'Sağlıksız'
  return <span className={`status-badge status-${state.toLowerCase()}`}><span aria-hidden="true" />{label}</span>
}
