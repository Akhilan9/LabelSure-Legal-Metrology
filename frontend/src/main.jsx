import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import ProtectedRoute from './auth/ProtectedRoute'
import AppLayout from './components/AppLayout'
import Login from './pages/Login'
import ComingSoon from './pages/ComingSoon'
import Reports from './pages/Reports'
import FieldCapture from './pages/FieldCapture'
import RulesRepository from './pages/RulesRepository'
import NewInspection from './pages/NewInspection'
import InspectionsList from './pages/InspectionsList'
import InspectionDetail from './pages/InspectionDetail'
import './styles.css'
import './auth.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<App />} />
              <Route path="/inspections" element={<InspectionsList />} />
              <Route path="/inspections/:id" element={<InspectionDetail />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/field" element={<FieldCapture />} />
              <Route path="/forbidden" element={<ComingSoon title="Access restricted" forbidden />} />
              <Route element={<ProtectedRoute roles={['INSPECTOR']} />}>
                <Route path="/inspections/new" element={<NewInspection />} />
              </Route>
              <Route element={<ProtectedRoute roles={['INSPECTOR']} />}>
                <Route path="/rules" element={<RulesRepository />} />
              </Route>
            </Route>
          </Route>
          <Route
            path="*"
            element={
              <main className="p-12 text-center">
                <h1 className="text-2xl font-serif mb-2">Page not found</h1>
                <Link to="/" className="text-emerald-900 underline">
                  Return to LabelSure
                </Link>
              </main>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => {}) })
}
