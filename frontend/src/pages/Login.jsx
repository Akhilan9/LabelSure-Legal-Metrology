import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { login, authenticated, loading, sessionError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  if (loading) return <main role="status">Verifying your session…</main>
  if (authenticated) return <Navigate to="/dashboard" replace />
  async function submit(event) {
    event.preventDefault(); setError('')
    if (!email.trim() || !password) { setError('Enter your email address and password.'); return }
    setBusy(true)
    try {
      await login(email.trim(), password)
      const destination = location.state?.from
      navigate(typeof destination === 'string' && destination.startsWith('/') && !destination.startsWith('//')
        && destination !== '/login' ? destination : '/dashboard', { replace: true })
    } catch (err) {
      setError(err.response?.status === 401 ? 'Email or password is incorrect, or your account is inactive.'
        : err.response?.status === 422 ? 'Check your email address and password format.'
        : err.response?.status === 503 ? 'Sign-in is not configured. Contact your administrator.'
        : 'Unable to sign in. Check that the API is running and try again.')
    } finally { setBusy(false) }
  }
  return <div className="login-shell"><section className="login-story">
    <div className="brand"><span className="mark">L<span>✓</span></span><span>LabelSure<small>APEX / SIH 26034</small></span></div>
    <div className="login-intro"><div className="eyebrow">REGULATORY INSPECTION WORKSPACE</div><h1>Inspection workspace.<br/><em>Evidence-led decisions.</em></h1><p>A dedicated workspace for packaged commodity inspection, built around the people responsible for review.</p></div>
    <div className="login-principle"><span>01 / IDENTITY & ACCESS</span><p>One workspace. Verified inspectors.<br/>A clear boundary for every action.</p></div><small>TEAM APEX · SMART INDIA HACKATHON 2026</small>
  </section><main className="login-main"><div className="login-card"><span className="phase-badge">AUTHORIZED PERSONNEL</span>
    <h2>Sign in to LabelSure</h2><p className="muted">Sign in with your inspector account.</p>
    <form onSubmit={submit}>{(error || sessionError) && <div className="auth-error" role="alert">{error || sessionError}</div>}
      <label htmlFor="email">Official email address</label><input id="email" type="email" autoComplete="username" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} placeholder="name@labelsure.local" disabled={busy} />
      <label htmlFor="password">Password</label><div className="password-field"><input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required maxLength={1024} value={password} onChange={e => setPassword(e.target.value)} disabled={busy} /><button type="button" className="password-toggle" onClick={() => setShowPassword(v => !v)} aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}>{showPassword ? 'Hide' : 'Show'}</button></div>
      <button className="login-submit" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to workspace'}<span aria-hidden="true">↗</span></button>
    </form><p className="login-help">For an account or password reset, contact your workspace operator.</p><div className="login-footnote">LabelSure · Inspection support platform<br/>SIH 26034 / Team APEX prototype</div>
  </div></main></div>
}
