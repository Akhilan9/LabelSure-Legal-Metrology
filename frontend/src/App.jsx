import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from './api/client'
import { useAuth } from './auth/AuthContext'
import EnforcementReviewQueue from './components/EnforcementReviewQueue'
import EnforcementAnalytics from './components/EnforcementAnalytics'

const stages = [
  'Capture & OpenCV Quality',
  'PaddleOCR & Extraction',
  'Context & Legal Rules',
  'RuleLens & Officer Review',
  'ReportLab PDF & Audit History',
]

export default function App() {
  const { user } = useAuth()
  const [health, setHealth] = useState({ state: 'checking' })
  const [attempt, setAttempt] = useState(0)
  const [summary, setSummary] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    setHealth({ state: 'checking' })
    api
      .get('/health', { signal: controller.signal })
      .then(({ data }) => {
        setHealth({ state: data.status === 'ok' ? 'connected' : 'degraded', data })
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setHealth({ state: error.response?.status === 503 ? 'degraded' : 'offline' })
        }
      })
    return () => controller.abort()
  }, [attempt])

  useEffect(() => {
    let isMounted = true
    api
      .get('/dashboard/summary')
      .then(({ data }) => {
        if (isMounted) {
          setSummary(data)
          setSummaryLoading(false)
        }
      })
      .catch(() => {
        if (isMounted) {
          setSummaryLoading(false)
        }
      })
    return () => {
      isMounted = false
    }
  }, [])

  return (
    <div className="space-y-8">
      {/* Hero Banner with Dark Ambient Glow */}
      <section className="relative overflow-hidden rounded-2xl glass-panel p-8 sm:p-10 border border-slate-800 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-1/3 -mb-12 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
          <div className="max-w-2xl space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
              <span>⚡ AI-Powered Compliance Enforcement</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-extrabold font-serif text-white tracking-tight leading-tight">
              APEX LabelSure <br />
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                Legal Metrology Intelligence
              </span>
            </h1>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              Automated packaging inspection platform for India's Legal Metrology (Packaged Commodities) Rules, 2011–2026. Extract statutory declarations, evaluate legal rule compliance, and adjudicate with traceable RuleLens evidence.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <Link
                to="/inspections/new"
                className="w-auto px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold text-sm rounded-xl shadow-lg shadow-emerald-500/25 transition-all transform hover:-translate-y-0.5"
              >
                + Start New Inspection
              </Link>
              <Link
                to="/field"
                className="w-auto px-6 py-3 bg-slate-900/80 hover:bg-slate-800 text-slate-200 font-semibold text-sm rounded-xl border border-slate-700 backdrop-blur-md transition-all"
              >
                📷 Open Offline Scanner
              </Link>
            </div>
          </div>

          {/* Hero Seal Emblem */}
          <div className="hidden lg:flex flex-col items-center justify-center w-40 h-40 rounded-full border-2 border-emerald-500/30 bg-emerald-950/20 backdrop-blur-md shadow-2xl relative group">
            <div className="absolute inset-0 rounded-full bg-emerald-500/10 animate-ping opacity-25"></div>
            <span className="text-4xl font-serif font-bold text-emerald-400">L✓</span>
            <span className="text-[9px] font-mono font-bold tracking-widest text-slate-400 uppercase mt-2">
              SIH 2026 #26034
            </span>
          </div>
        </div>
      </section>

      {/* Metrics Grid Cards */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 font-mono">
            Operational Workspace Metrics
          </h2>
          <Link
            to="/inspections"
            className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1"
          >
            <span>View All Records</span>
            <span>→</span>
          </Link>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-card rounded-2xl p-5 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
              <span>TOTAL RECORDS</span>
              <span className="text-base">📁</span>
            </div>
            <div className="text-3xl font-extrabold font-mono text-white mt-2">
              {summaryLoading ? '…' : summary ? summary.total_inspections : 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Stored in sqlite/postgres repository</p>
          </div>

          <div className="glass-card rounded-2xl p-5 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
              <span>DRAFTS</span>
              <span className="text-base">📝</span>
            </div>
            <div className="text-3xl font-extrabold font-mono text-amber-400 mt-2">
              {summaryLoading ? '…' : summary ? summary.draft_count : 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Awaiting photo evidence</p>
          </div>

          <div className="glass-card rounded-2xl p-5 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
              <span>EVIDENCE STAGED</span>
              <span className="text-base">📸</span>
            </div>
            <div className="text-3xl font-extrabold font-mono text-cyan-400 mt-2">
              {summaryLoading ? '…' : summary ? summary.evidence_uploaded_count : 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Uploaded & quality assessed</p>
          </div>

          <div className="glass-card rounded-2xl p-5 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
              <span>READY FOR RULES</span>
              <span className="text-base">⚡</span>
            </div>
            <div className="text-3xl font-extrabold font-mono text-emerald-400 mt-2">
              {summaryLoading ? '…' : summary ? summary.ready_for_analysis_count : 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Queued for rule evaluation</p>
          </div>
        </div>
      </section>

      {/* Enforcement Analytics & Review Queue */}
      <EnforcementAnalytics user={user} />
      <EnforcementReviewQueue user={user} />

      {/* Recent Inspections Table */}
      {summary && summary.recent_inspections && summary.recent_inspections.length > 0 && (
        <section className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-base font-serif font-bold text-white">Recent Inspection Activity</h2>
            <Link to="/inspections" className="text-xs text-emerald-400 hover:underline font-semibold">
              Full Case Explorer →
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-slate-400 uppercase text-[10px] border-b border-slate-800 font-mono">
                  <th className="pb-3">Code</th>
                  <th className="pb-3">Commodity Name</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Photos</th>
                  <th className="pb-3">Created</th>
                  <th className="pb-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {summary.recent_inspections.map((insp) => (
                  <tr key={insp.id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="py-3 font-mono font-bold text-emerald-400">{insp.inspection_code}</td>
                    <td className="py-3 text-slate-200 font-medium">{insp.product_name || '—'}</td>
                    <td className="py-3">
                      <span className="px-2.5 py-1 bg-slate-900 border border-slate-700 rounded-md text-[10px] font-bold text-slate-300">
                        {insp.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400 font-mono">{insp.images_count} panels</td>
                    <td className="py-3 text-slate-400">{new Date(insp.created_at).toLocaleDateString()}</td>
                    <td className="py-3 text-right">
                      <Link
                        to={`/inspections/${insp.id}`}
                        className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-lg text-xs font-semibold transition-colors"
                      >
                        Open Workspace →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Inspection Journey & Service Health Grid */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Journey Steps */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-base font-serif font-bold text-white">Regulatory Inspection Pipeline</h3>
            <span className="text-[10px] font-mono font-bold bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
              LMPC 2011–2026
            </span>
          </div>
          <p className="text-xs text-slate-400">Traceable workflow progression from raw package evidence to court-admissible certificates.</p>
          <div className="space-y-2.5 pt-2">
            {stages.map((stage, i) => (
              <div key={stage} className="flex items-center gap-4 p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
                <span className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono font-bold flex items-center justify-center shrink-0">
                  0{i + 1}
                </span>
                <span className="font-semibold text-slate-200">{stage}</span>
                <span className="ml-auto text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded">
                  Operational
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Backend Health Service Box */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-serif font-bold text-white">API Engine Status</h3>
              <span
                className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${
                  health.state === 'connected'
                    ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                    : 'bg-rose-950 text-rose-400 border-rose-800'
                }`}
              >
                {health.state.toUpperCase()}
              </span>
            </div>
            <dl className="space-y-3 pt-3 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <dt className="text-slate-400">Service</dt>
                <dd className="font-mono font-semibold text-white">FastAPI Backend</dd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <dt className="text-slate-400">OCR Engine</dt>
                <dd className="font-mono font-semibold text-emerald-400">PaddleOCR PP-OCRv6</dd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <dt className="text-slate-400">Database</dt>
                <dd className="font-mono font-semibold text-slate-200">{health.data?.database || 'SQLite / Postgres'}</dd>
              </div>
              <div className="flex justify-between py-1">
                <dt className="text-slate-400">Report Engine</dt>
                <dd className="font-mono font-semibold text-slate-200">ReportLab PDF</dd>
              </div>
            </dl>
          </div>
          <button
            type="button"
            disabled={health.state === 'checking'}
            onClick={() => setAttempt((v) => v + 1)}
            className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 transition-colors"
          >
            Re-verify API Connection 🔄
          </button>
        </div>
      </section>

      {/* Core Architectural Mandates */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
        {[
          ['01', 'AI Observes', 'OCR models localize visible declarations as evidence.'],
          ['02', 'Rules Decide', 'Versioned legal rulesets enforce LMPC requirements.'],
          ['03', 'Evidence Explains', 'RuleLens links findings to photographic coordinates.'],
          ['04', 'Inspector Verifies', 'Officers maintain accountable adjudication overrides.'],
        ].map(([n, title, detail]) => (
          <div key={n} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-1.5">
            <span className="text-[10px] font-mono font-bold text-emerald-400">{n}</span>
            <h4 className="text-xs font-bold text-white">{title}</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">{detail}</p>
          </div>
        ))}
      </section>

      <footer className="pt-6 border-t border-slate-800 text-center text-xs text-slate-500 font-mono">
        APEX LabelSure · Legal Metrology Packaging Compliance Platform · SIH 2026 #26034
      </footer>
    </div>
  )
}
