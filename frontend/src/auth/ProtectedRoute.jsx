import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

export default function ProtectedRoute({ roles }) {
  const { user, authenticated, loading } = useAuth()
  const location = useLocation()
  if (loading) return <main role="status">Verifying your session…</main>
  if (!authenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(user.role)) return <Navigate to="/forbidden" replace />
  return <Outlet />
}
