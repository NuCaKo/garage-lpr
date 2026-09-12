import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { CurrentUser } from '../types'

interface AuthenticationPageProps {
  mode: 'setup' | 'login'
  onAuthenticated: (user: CurrentUser) => void
}

export function AuthenticationPage({ mode, onAuthenticated }: AuthenticationPageProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const errorRef = useRef<HTMLDivElement>(null)
  const isSetup = mode === 'setup'

  useEffect(() => {
    if (error) errorRef.current?.focus()
  }, [error])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (isSetup && password !== confirmation) {
      setError('Parola ve doğrulama alanları aynı olmalıdır.')
      return
    }
    setSubmitting(true)
    try {
      const user = isSetup
        ? await api.setupAdmin(username.trim(), password, confirmation)
        : await api.login(username.trim(), password)
      onAuthenticated(user)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Kimlik doğrulama başarısız oldu.')
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="auth-shell" id="main-content">
    <section className="auth-card" aria-labelledby="auth-title">
      <div className="auth-brand">
        <span className="brand-mark" aria-hidden="true"><span /></span>
        <div><strong>Garage LPR</strong><small>Yerel edge control</small></div>
      </div>
      <p className="eyebrow">{isSetup ? 'İlk kurulum · Admin hesabı' : 'Güvenli yönetim'}</p>
      <h1 id="auth-title">{isSetup ? 'Sistemi sahiplenin' : 'Oturum açın'}</h1>
      <p className="auth-intro">{isSetup
        ? 'İlk ve tek başlangıç admin hesabını oluşturun. Parola yalnızca Argon2id hash olarak saklanır.'
        : 'Kamera, araç ve gate ayarlarına erişmek için yönetici hesabınızı kullanın.'}</p>
      {error && <div ref={errorRef} className="alert alert-error" role="alert" tabIndex={-1}>
        <strong>İşlem tamamlanamadı.</strong><span>{error}</span>
      </div>}
      <form className="auth-form" onSubmit={submit}>
        <label className="field" htmlFor="auth-username"><span>Kullanıcı adı</span>
          <input id="auth-username" name="username" autoComplete="username" required minLength={3} maxLength={80} pattern="[A-Za-z0-9_.-]+" value={username} onChange={(event) => setUsername(event.target.value)} />
          {isSetup && <small>Harf, rakam, nokta, tire ve alt çizgi kullanılabilir.</small>}
        </label>
        <label className="field" htmlFor="auth-password"><span>Parola</span>
          <input id="auth-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete={isSetup ? 'new-password' : 'current-password'} required minLength={isSetup ? 12 : 1} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} />
          {isSetup && <small>En az 12 karakter; kullanıcı adını içermemelidir.</small>}
        </label>
        {isSetup && <label className="field" htmlFor="auth-confirmation"><span>Parolayı doğrula</span>
          <input id="auth-confirmation" name="password-confirmation" type={showPassword ? 'text' : 'password'} autoComplete="new-password" required minLength={12} maxLength={128} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
        </label>}
        <label className="password-visibility"><input type="checkbox" checked={showPassword} onChange={(event) => setShowPassword(event.target.checked)} /><span>Parolayı göster</span></label>
        <button className="primary-button auth-submit" type="submit" disabled={submitting}>{submitting ? 'Doğrulanıyor…' : isSetup ? 'Admin hesabını oluştur' : 'Oturum aç'}</button>
      </form>
      <p className="auth-footnote">İnternet bağlantısı gerekmez · Session tokenları ham biçimde saklanmaz</p>
    </section>
  </main>
}
