import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api, setAccessToken, setUnauthorizedHandler } from '../api/client'

/** @type {import("react").Context<any>} */
const AuthContext = createContext(null)
const key = 'labelsure.session'
function readSession() { try { return JSON.parse(sessionStorage.getItem(key)) } catch { return null } }
function saveSession(value) {
  try { if (value) sessionStorage.setItem(key, JSON.stringify(value)); else sessionStorage.removeItem(key) } catch { /* In-memory session still works. */ }
}
export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sessionError, setSessionError] = useState('')
  const revision = useRef(0)
  const logout = useCallback((message = '') => {
    revision.current += 1
    setAccessToken(null); saveSession(null); setSession(null); setUser(null)
    setLoading(false); setSessionError(message)
  }, [])
  const loadCurrentUser = useCallback(async () => {
    const current = readSession()
    if (!current?.token || !Number.isFinite(current.expiresAt) || current.expiresAt <= Date.now()) {
      logout(current ? 'Your session expired. Please sign in again.' : '')
      return
    }
    const requestRevision = ++revision.current
    setAccessToken(current.token); setLoading(true)
    try {
      const { data } = await api.get('/auth/me')
      if (requestRevision === revision.current) { setSession(current); setUser(data); setSessionError('') }
    } catch (error) {
      if (requestRevision === revision.current) logout(error.response?.status === 401
        ? 'Your session expired. Please sign in again.'
        : 'Unable to verify your session. Check the connection and sign in again.')
    } finally { if (requestRevision === revision.current) setLoading(false) }
  }, [logout])
  useEffect(() => setUnauthorizedHandler(() => logout('Your session expired. Please sign in again.')), [logout])
  useEffect(() => { loadCurrentUser() }, [loadCurrentUser])
  useEffect(() => {
    if (!session?.expiresAt) return
    const timer = setTimeout(() => logout('Your session expired. Please sign in again.'), Math.max(0, session.expiresAt - Date.now()))
    return () => clearTimeout(timer)
  }, [session, logout])
  async function login(email, password) {
    const { data } = await api.post('/auth/login', { email, password })
    revision.current += 1
    const current = { token: data.access_token, expiresAt: Date.now() + data.expires_in * 1000 }
    setAccessToken(current.token); saveSession(current); setSession(current)
    setUser(data.user); setSessionError(''); setLoading(false)
    return data.user
  }
  return <AuthContext.Provider value={{ user, accessToken: session?.token || null,
    authenticated: Boolean(user), loading, sessionError, login, logout, loadCurrentUser }}>{children}</AuthContext.Provider>
}
export function useAuth() { return useContext(AuthContext) }
