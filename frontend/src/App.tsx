import { useCallback, useEffect, useRef, useState, type ComponentType, type SVGProps } from 'react'
import { api } from './api'
import { CameraIcon, CarIcon, DashboardIcon, EventIcon, GateIcon, HealthIcon, RuleIcon, SettingsIcon } from './components/Icons'
import { Dashboard } from './pages/Dashboard'
import { CamerasPage } from './pages/Cameras'
import { Placeholder } from './pages/Placeholder'
import { SettingsPage } from './pages/Settings'
import { VehiclesPage } from './pages/Vehicles'
import { GateControllersPage } from './pages/GateControllers'
import { AccessRulesPage } from './pages/AccessRules'
import { EventsPage } from './pages/Events'
import { SystemHealthPage } from './pages/SystemHealth'
import { AuthenticationPage } from './pages/Authentication'
import type { CurrentUser, InferenceMetrics, ResourceMetrics, SystemHealth } from './types'

type PageId = 'dashboard' | 'cameras' | 'vehicles' | 'gates' | 'rules' | 'events' | 'settings' | 'health'
type IconComponent = ComponentType<SVGProps<SVGSVGElement>>

const navigation: Array<{ id: PageId; label: string; icon: IconComponent }> = [
  { id: 'dashboard', label: 'Dashboard', icon: DashboardIcon },
  { id: 'cameras', label: 'Kameralar', icon: CameraIcon },
  { id: 'vehicles', label: 'Araçlar', icon: CarIcon },
  { id: 'gates', label: 'Gate controllers', icon: GateIcon },
  { id: 'rules', label: 'Erişim kuralları', icon: RuleIcon },
  { id: 'events', label: 'Olaylar', icon: EventIcon },
  { id: 'settings', label: 'Sistem ayarları', icon: SettingsIcon },
  { id: 'health', label: 'Sistem sağlığı', icon: HealthIcon },
]
const HEALTH_POLL_INTERVAL_MS = 10_000

function initialPage(): PageId {
  const candidate = window.location.hash.replace(/^#\/?/, '')
  return navigation.some((item) => item.id === candidate) ? candidate as PageId : 'dashboard'
}

export default function App() {
  const [authState, setAuthState] = useState<'loading' | 'setup' | 'login' | 'authenticated'>('loading')
  const [user, setUser] = useState<CurrentUser | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    async function bootstrapAuthentication() {
      try {
        const setup = await api.setupStatus(controller.signal)
        if (setup.setup_required) {
          setAuthState('setup')
          return
        }
        try {
          const current = await api.currentUser(controller.signal)
          setUser(current)
          setAuthState('authenticated')
        } catch {
          if (!controller.signal.aborted) setAuthState('login')
        }
      } catch {
        if (!controller.signal.aborted) setAuthState('login')
      }
    }
    const unauthorized = () => {
      setUser(null)
      setAuthState('login')
    }
    window.addEventListener('garage-lpr:unauthorized', unauthorized)
    void bootstrapAuthentication()
    return () => {
      controller.abort()
      window.removeEventListener('garage-lpr:unauthorized', unauthorized)
    }
  }, [])

  if (authState === 'loading') return <main className="auth-shell"><div className="auth-loading" aria-live="polite">Güvenli oturum denetleniyor…</div></main>
  if (authState === 'setup' || authState === 'login') return <AuthenticationPage mode={authState} onAuthenticated={(nextUser) => { setUser(nextUser); setAuthState('authenticated') }} />
  if (!user) return null
  return <AuthenticatedApp user={user} onSignedOut={() => { setUser(null); setAuthState('login') }} />
}

function AuthenticatedApp({ user, onSignedOut }: { user: CurrentUser; onSignedOut: () => void }) {
  const [page, setPage] = useState<PageId>(initialPage)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [inference, setInference] = useState<InferenceMetrics | null>(null)
  const [resources, setResources] = useState<ResourceMetrics | null>(null)
  const [pollIntervalMs, setPollIntervalMs] = useState(HEALTH_POLL_INTERVAL_MS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mainRef = useRef<HTMLElement>(null)

  const refreshHealth = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    try {
      const [nextHealth, nextInference, nextResources] = await Promise.all([
        api.health(signal), api.inferenceMetrics(signal), api.resourceMetrics(signal),
      ])
      setHealth(nextHealth)
      setInference(nextInference)
      setResources(nextResources)
      setError(null)
    } catch (reason) {
      if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Sağlık bilgisi alınamadı')
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    api.settings(controller.signal).then((settings) => {
      setPollIntervalMs(settings.metrics_poll_interval_seconds * 1000)
    }).catch(() => undefined)
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    let timer: number | null = null
    const poll = async () => {
      await refreshHealth(controller.signal)
      if (!controller.signal.aborted) timer = window.setTimeout(poll, pollIntervalMs)
    }
    timer = window.setTimeout(() => void poll(), 0)
    return () => {
      controller.abort()
      if (timer !== null) window.clearTimeout(timer)
    }
  }, [pollIntervalMs, refreshHealth])

  function navigate(nextPage: PageId) {
    setPage(nextPage)
    window.history.replaceState(null, '', `#/${nextPage}`)
    window.requestAnimationFrame(() => mainRef.current?.focus())
  }

  async function signOut() {
    try {
      await api.logout()
    } finally {
      onSignedOut()
    }
  }

  return <><a className="skip-link" href="#main-content">Ana içeriğe geç</a><div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark" aria-hidden="true"><span /></span><div><strong>Garage LPR</strong><small>Edge control</small></div></div>
      <nav aria-label="Ana navigasyon">
        {navigation.map(({ id, label, icon: Icon }) => <button type="button" key={id} className={page === id ? 'nav-item active' : 'nav-item'} aria-current={page === id ? 'page' : undefined} onClick={() => navigate(id)}><Icon /><span>{label}</span></button>)}
      </nav>
      <div className="sidebar-footer"><span className="safety-dot" aria-hidden="true"/><div><strong>Fail-safe aktif</strong><small>Simulation + maintenance</small></div></div>
    </aside>
    <main id="main-content" ref={mainRef} tabIndex={-1}>
      <header className="topbar"><span>Yerel kontrol merkezi</span><div className="topbar-actions"><span className="current-user"><strong>{user.username}</strong><small>{user.role}</small></span><button type="button" className="refresh-button" onClick={() => void refreshHealth()} disabled={loading}>Durumu yenile</button><button type="button" className="logout-button" onClick={() => void signOut()}>Oturumu kapat</button></div></header>
      <div className="page-content">{renderPage(page, health, inference, resources, loading, error)}</div>
    </main>
  </div></>
}

function renderPage(page: PageId, health: SystemHealth | null, inference: InferenceMetrics | null, resources: ResourceMetrics | null, loading: boolean, error: string | null) {
  if (page === 'dashboard') return <Dashboard health={health} inference={inference} resources={resources} loading={loading} error={error}/>
  if (page === 'health') return <SystemHealthPage health={health} resources={resources} loading={loading} error={error}/>
  if (page === 'cameras') return <CamerasPage />
  if (page === 'vehicles') return <VehiclesPage />
  if (page === 'gates') return <GateControllersPage />
  if (page === 'rules') return <AccessRulesPage />
  if (page === 'settings') return <SettingsPage />
  if (page === 'events') return <EventsPage />
  return <Placeholder title="Hazırlanıyor" description="Bu ekran henüz etkin değil." phase="Planlandı"/>
}
