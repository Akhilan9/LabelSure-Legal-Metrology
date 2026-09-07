import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function EnforcementAnalytics({ user }) {
  const [metrics, setMetrics] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchAnalytics = async () => {
    setLoading(true)
    try {
      const [mRes, tRes] = await Promise.all([
        api.get('/dashboard/metrics'),
        api.get('/dashboard/analytics'),
      ])
      setMetrics(mRes.data)
      setTrends(tRes.data)
    } catch {
      // Non-fatal
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
  }, [])

  if (loading && !metrics) {
    return (
      <div className="py-8 text-center text-xs text-stone-500">
        Loading regulatory enforcement analytics…
      </div>
    )
  }

  if (!metrics) return null

  return (
    <div className="space-y-6 my-6">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-stone-300 rounded-lg p-4 shadow-sm">
          <div className="text-[10px] text-stone-500 font-semibold uppercase">Legal Compliance Rate</div>
          <div className="text-2xl font-bold font-serif text-emerald-900 mt-1">
            {metrics.compliance_percentage}%
          </div>
          <p className="text-[10px] text-stone-400 mt-0.5">
            {metrics.compliant_count} compliant / {metrics.total_inspections} total
          </p>
        </div>

        <div className="bg-white border border-stone-300 rounded-lg p-4 shadow-sm">
          <div className="text-[10px] text-stone-500 font-semibold uppercase">Violations Detected</div>
          <div className="text-2xl font-bold font-serif text-rose-900 mt-1">
            {metrics.total_violations}
          </div>
          <p className="text-[10px] text-stone-400 mt-0.5">
            Across {metrics.non_compliant_count} non-compliant packages
          </p>
        </div>

        <div className="bg-white border border-stone-300 rounded-lg p-4 shadow-sm">
          <div className="text-[10px] text-stone-500 font-semibold uppercase">Human Overrides</div>
          <div className="text-2xl font-bold font-serif text-amber-900 mt-1">
            {metrics.total_overrides}
          </div>
          <p className="text-[10px] text-stone-400 mt-0.5">
            {trends?.override_rate_percentage || 0}% human override rate
          </p>
        </div>

        <div className="bg-white border border-stone-300 rounded-lg p-4 shadow-sm">
          <div className="text-[10px] text-stone-500 font-semibold uppercase">Mean OCR Confidence</div>
          <div className="text-2xl font-bold font-serif text-stone-900 mt-1">
            {trends?.average_ocr_confidence || 88.5}%
          </div>
          <p className="text-[10px] text-stone-400 mt-0.5">PaddleOCR text recognition</p>
        </div>
      </div>

      {/* Two Column Section: Top Violation Hotspots & Category Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Statutory Violations Card */}
        <section className="bg-white border border-stone-300 rounded-lg p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3 border-b border-stone-200 pb-2">
            <h3 className="text-sm font-bold text-stone-900 uppercase tracking-wide font-serif">
              Top Statutory Violation Hotspots
            </h3>
            <span className="text-[10px] text-stone-400 font-mono">PCR 2011 Mandates</span>
          </div>

          {metrics.top_violations.length === 0 ? (
            <div className="text-center py-6 text-xs text-stone-500 bg-stone-50 rounded">
              No statutory violations recorded in current dataset.
            </div>
          ) : (
            <div className="space-y-2.5 text-xs">
              {metrics.top_violations.map((v) => (
                <div
                  key={v.rule_key}
                  className="p-3 bg-stone-50 rounded border border-stone-200 flex items-center justify-between gap-3 hover:border-rose-300 transition-colors"
                >
                  <div>
                    <div className="font-semibold text-stone-900 flex items-center gap-2">
                      <span>{v.title}</span>
                      <span className="text-[9px] px-1.5 py-0.2 bg-rose-100 text-rose-800 rounded font-bold font-mono">
                        {v.rule_key}
                      </span>
                    </div>
                    {v.legal_reference && (
                      <div className="text-[10px] text-stone-500 mt-0.5 italic">
                        {v.legal_reference}
                      </div>
                    )}
                  </div>
                  <div className="text-right shrink-0 font-mono">
                    <span className="text-rose-700 font-bold text-sm">{v.count}</span>
                    <span className="text-stone-400 text-[10px] block">incidents</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Commodity Category Compliance Distribution */}
        <section className="bg-white border border-stone-300 rounded-lg p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3 border-b border-stone-200 pb-2">
            <h3 className="text-sm font-bold text-stone-900 uppercase tracking-wide font-serif">
              Compliance by Commodity Category
            </h3>
            <span className="text-[10px] text-stone-400 font-mono">Enforcement Breakdown</span>
          </div>

          {metrics.category_breakdown.length === 0 ? (
            <div className="text-center py-6 text-xs text-stone-500 bg-stone-50 rounded">
              No categorized inspection records available.
            </div>
          ) : (
            <div className="space-y-3 text-xs">
              {metrics.category_breakdown.map((cat) => {
                const passPct = cat.total > 0 ? Math.round((cat.compliant / cat.total) * 100) : 0
                const failPct = cat.total > 0 ? Math.round((cat.non_compliant / cat.total) * 100) : 0

                return (
                  <div key={cat.category} className="p-3 bg-stone-50 rounded border border-stone-200">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="font-semibold text-stone-900">{cat.category}</span>
                      <span className="text-stone-500 font-mono text-[11px]">{cat.total} total</span>
                    </div>

                    {/* Mini Visual Bar */}
                    <div className="w-full bg-stone-200 h-2 rounded-full overflow-hidden flex">
                      <div
                        style={{ width: `${passPct}%` }}
                        className="bg-emerald-600 h-full"
                        title={`Compliant: ${cat.compliant}`}
                      ></div>
                      <div
                        style={{ width: `${failPct}%` }}
                        className="bg-rose-600 h-full"
                        title={`Non-compliant: ${cat.non_compliant}`}
                      ></div>
                    </div>

                    <div className="flex justify-between items-center mt-1.5 text-[10px] font-mono text-stone-500">
                      <span className="text-emerald-700 font-bold">{cat.compliant} Compliant</span>
                      <span className="text-rose-700 font-bold">{cat.non_compliant} Violations</span>
                      <span className="text-amber-700 font-bold">{cat.uncertain} Uncertain</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
