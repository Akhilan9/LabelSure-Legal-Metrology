import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const navigation = [
  ['/dashboard', 'Dashboard', '📊', ['INSPECTOR']],
  ['/inspections/new', 'New Inspection', '➕', ['INSPECTOR']],
  ['/inspections', 'Inspections Repository', '📁', ['INSPECTOR']],
  ['/reports', 'Compliance Reports', '📑', ['INSPECTOR']],
  ['/field', 'Offline Scanner', '📷', ['INSPECTOR']],
  ['/rules', 'Rule Repository', '📜', ['INSPECTOR']],
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-[#090d16] text-slate-100 font-sans selection:bg-emerald-500/30">
      {/* Mobile Top Header Bar */}
      <div className="lg:hidden flex items-center justify-between p-4 bg-slate-900/90 border-b border-slate-800 backdrop-blur-md sticky top-0 z-40">
        <NavLink to="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-600 to-cyan-500 flex items-center justify-center font-bold text-white shadow-lg shadow-emerald-500/20">
            L✓
          </div>
          <span className="font-bold text-lg text-white font-serif tracking-tight">LabelSure</span>
        </NavLink>
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-slate-400 hover:text-white rounded-lg bg-slate-800/80 border border-slate-700 w-auto"
        >
          {mobileMenuOpen ? '✕ Close' : '☰ Menu'}
        </button>
      </div>

      {/* Sidebar Navigation Panel */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-72 bg-slate-950/95 lg:bg-slate-950 border-r border-slate-800/80 p-6 flex flex-col transition-transform duration-300 ease-in-out backdrop-blur-xl ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Logo */}
        <NavLink to="/dashboard" className="flex items-center gap-3 group mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-cyan-400 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-emerald-500/25 group-hover:scale-105 transition-transform">
            L✓
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-xl text-white font-serif tracking-tight">LabelSure</span>
              <span className="text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">APEX</span>
            </div>
            <span className="text-[10px] text-slate-400 tracking-wider uppercase font-mono">Legal Metrology AI</span>
          </div>
        </NavLink>

        {/* Navigation Category Header */}
        <div className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-3 px-3">
          Inspection Platform
        </div>

        {/* Main Nav Links */}
        <nav aria-label="Main navigation" className="space-y-1.5 flex-1">
          {navigation
            .filter(([, , , roles]) => !user || roles.includes(user.role))
            .map(([path, label, icon]) => {
              const isActive = location.pathname === path || (path !== '/dashboard' && location.pathname.startsWith(path))

              return (
                <NavLink
                  to={path}
                  key={path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3.5 py-3 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-emerald-600/20 to-cyan-600/10 text-emerald-300 border border-emerald-500/30 shadow-lg shadow-emerald-950/50'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/80 border border-transparent'
                  }`}
                >
                  <span className="text-base">{icon}</span>
                  <span>{label}</span>
                  {isActive && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400"></span>}
                </NavLink>
              )
            })}
        </nav>

        {/* User Account Profile Pill */}
        <div className="mt-auto pt-6 border-t border-slate-800/80">
          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 font-mono">
                  {user?.role || 'INSPECTOR'}
                </span>
              </div>
              <p className="text-xs font-semibold text-white truncate mt-0.5">{user?.full_name || 'Legal Officer'}</p>
              <p className="text-[10px] text-slate-500 truncate">{user?.email || 'officer@labelsure.local'}</p>
            </div>
            <button
              type="button"
              onClick={() => logout()}
              title="Sign Out"
              className="w-auto p-2 bg-slate-800 hover:bg-rose-950/50 hover:text-rose-400 hover:border-rose-900 text-slate-400 rounded-lg border border-slate-700 transition-colors shrink-0"
            >
              🚪
            </button>
          </div>
        </div>
      </aside>

      {/* Main Workspace Right Canvas */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400 hidden sm:inline">OFFICIAL INSPECTION SYSTEM</span>
            <span className="text-slate-700 hidden sm:inline">•</span>
            <span className="text-xs font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-1 rounded-md">
              LMPC RULES 2011–2026 ENFORCEMENT
            </span>
          </div>

          <div className="flex items-center gap-4 text-xs text-slate-400">
            <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-mono text-[11px] text-slate-300">FastAPI & OpenCV Engine Online</span>
            </div>
          </div>
        </header>

        {/* Page Content Outlet */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
