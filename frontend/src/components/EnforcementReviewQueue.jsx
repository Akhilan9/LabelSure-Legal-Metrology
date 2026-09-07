import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

const URGENCY_TIER_STYLES = {
  CRITICAL: 'bg-rose-100 text-rose-800 border-rose-300 font-bold',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-300 font-bold',
  MEDIUM: 'bg-amber-100 text-amber-800 border-amber-300 font-medium',
  LOW: 'bg-emerald-100 text-emerald-800 border-emerald-300 font-medium',
}

const COMPLIANCE_STYLES = {
  COMPLIANT: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  PASS: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  NON_COMPLIANT: 'bg-rose-100 text-rose-800 border-rose-300',
  FAIL: 'bg-rose-100 text-rose-800 border-rose-300',
  UNCERTAIN: 'bg-amber-100 text-amber-800 border-amber-300',
  PENDING: 'bg-stone-100 text-stone-600 border-stone-300',
}

export default function EnforcementReviewQueue({ user }) {
  const [queueData, setQueueData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [urgencyFilter, setUrgencyFilter] = useState('ALL')
  const [categoryFilter, setCategoryFilter] = useState('')

  const fetchQueue = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter && statusFilter !== 'ALL') params.append('status', statusFilter)
      if (urgencyFilter && urgencyFilter !== 'ALL') params.append('urgency', urgencyFilter)
      if (categoryFilter) params.append('category', categoryFilter)

      const { data } = await api.get(`/dashboard/review-queue?${params.toString()}`)
      setQueueData(data)
    } catch {
      setQueueData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
  }, [statusFilter, urgencyFilter, categoryFilter])

  return (
    <section className="bg-white border border-stone-300 rounded-lg p-6 shadow-sm my-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 border-b border-stone-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-stone-900 uppercase tracking-wide font-serif">
              Prioritized Inspector Review Queue
            </h2>
            {queueData && (
              <span className="text-xs bg-stone-100 px-2.5 py-0.5 rounded-full font-mono text-stone-700 font-semibold border border-stone-300">
                {queueData.total} {queueData.total === 1 ? 'Record' : 'Records'}
              </span>
            )}
          </div>
          <p className="text-xs text-stone-500 mt-0.5">
            Algorithmic urgency scoring prioritized by non-compliant rules, low-confidence OCR, overrides, and SLA age.
          </p>
        </div>

        {/* Urgency Scorecard Badges */}
        {queueData && (
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <button
              type="button"
              onClick={() => setUrgencyFilter(urgencyFilter === 'CRITICAL' ? 'ALL' : 'CRITICAL')}
              className={`px-2.5 py-1 rounded border transition-all ${
                urgencyFilter === 'CRITICAL' ? 'ring-2 ring-rose-500 shadow' : ''
              } bg-rose-50 text-rose-900 border-rose-200 font-medium`}
            >
              🔥 <strong>{queueData.critical_count}</strong> Critical
            </button>
            <button
              type="button"
              onClick={() => setUrgencyFilter(urgencyFilter === 'HIGH' ? 'ALL' : 'HIGH')}
              className={`px-2.5 py-1 rounded border transition-all ${
                urgencyFilter === 'HIGH' ? 'ring-2 ring-orange-500 shadow' : ''
              } bg-orange-50 text-orange-900 border-orange-200 font-medium`}
            >
              ⚠️ <strong>{queueData.high_count}</strong> High
            </button>
            <button
              type="button"
              onClick={() => setUrgencyFilter(urgencyFilter === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
              className={`px-2.5 py-1 rounded border transition-all ${
                urgencyFilter === 'MEDIUM' ? 'ring-2 ring-amber-500 shadow' : ''
              } bg-amber-50 text-amber-900 border-amber-200 font-medium`}
            >
              🟡 <strong>{queueData.medium_count}</strong> Medium
            </button>
            <button
              type="button"
              onClick={() => setUrgencyFilter('ALL')}
              className={`px-2.5 py-1 rounded border transition-all ${
                urgencyFilter === 'ALL' ? 'bg-stone-800 text-white' : 'bg-stone-100 text-stone-700 border-stone-300'
              } font-medium`}
            >
              All Tiers
            </button>
          </div>
        )}
      </div>

      {/* Filter Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 bg-stone-50 p-3 rounded-lg border border-stone-200 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-stone-500 font-semibold uppercase text-[10px]">Filter Status:</span>
          {['ALL', 'NEEDS_REVIEW', 'UNDER_REVIEW', 'FINALIZED'].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`w-auto px-2.5 py-1 rounded text-xs transition-colors ${
                statusFilter === st
                  ? 'bg-emerald-900 text-white font-bold'
                  : 'bg-white text-stone-700 border border-stone-300 hover:bg-stone-100'
              }`}
            >
              {st.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-stone-500 font-semibold uppercase text-[10px]">Category:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="text-xs bg-white border border-stone-300 rounded px-2.5 py-1 text-stone-800"
          >
            <option value="">All Categories</option>
            <option value="FOOD">Packaged Food</option>
            <option value="BEVERAGES">Beverages</option>
            <option value="COSMETICS">Cosmetics & Personal Care</option>
            <option value="ELECTRONICS">Electronics & Appliances</option>
            <option value="PHARMACEUTICALS">Pharmaceuticals</option>
            <option value="GENERAL">General Commodities</option>
          </select>
        </div>
      </div>

      {/* Review Queue Table */}
      {loading ? (
        <div className="py-12 text-center text-xs text-stone-500">
          Calculating urgency priority scores…
        </div>
      ) : queueData && queueData.items.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-stone-500 uppercase text-[10px] border-b border-stone-200">
                <th className="py-2.5 px-3">Urgency</th>
                <th className="py-2.5 px-3">Inspection Code</th>
                <th className="py-2.5 px-3">Product / Commodity</th>
                <th className="py-2.5 px-3">Compliance</th>
                <th className="py-2.5 px-3">Rule Violations</th>
                <th className="py-2.5 px-3">Review State</th>
                <th className="py-2.5 px-3">Age</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {queueData.items.map((item) => {
                const tierClass = URGENCY_TIER_STYLES[item.urgency_tier] || URGENCY_TIER_STYLES.LOW
                const compClass = COMPLIANCE_STYLES[item.overall_compliance] || COMPLIANCE_STYLES.PENDING

                return (
                  <tr key={item.inspection_id} className="hover:bg-stone-50 transition-colors">
                    {/* Urgency Badge & Score */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] border ${tierClass}`}>
                          {item.urgency_tier}
                        </span>
                        <span className="font-mono text-[10px] text-stone-400">({item.urgency_score})</span>
                      </div>
                    </td>

                    {/* Inspection Code */}
                    <td className="py-3 px-3 font-mono font-semibold text-stone-900">
                      <Link to={`/inspections/${item.inspection_id}`} className="hover:underline text-emerald-950">
                        {item.inspection_code}
                      </Link>
                    </td>

                    {/* Product & Category */}
                    <td className="py-3 px-3">
                      <div className="font-semibold text-stone-900 max-w-[200px] truncate">
                        {item.product_name || '—'}
                      </div>
                      <div className="text-[10px] text-stone-500 flex items-center gap-1.5 mt-0.5">
                        {item.brand_name && <span>{item.brand_name}</span>}
                        {item.category && (
                          <span className="bg-stone-100 px-1 py-0.2 rounded font-mono text-[9px]">
                            {item.category}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Overall Compliance */}
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${compClass}`}>
                        {item.overall_compliance}
                      </span>
                    </td>

                    {/* Violations Ledger */}
                    <td className="py-3 px-3 font-mono text-[11px]">
                      {item.violation_count > 0 ? (
                        <span className="text-rose-700 font-bold">❌ {item.violation_count} Fail</span>
                      ) : item.uncertain_count > 0 ? (
                        <span className="text-amber-700 font-semibold">⚠️ {item.uncertain_count} Uncertain</span>
                      ) : (
                        <span className="text-emerald-700">✓ {item.pass_count} Pass</span>
                      )}
                      {item.override_count > 0 && (
                        <span className="ml-2 text-[9px] bg-amber-50 text-amber-900 border border-amber-200 px-1 py-0.2 rounded">
                          {item.override_count} over
                        </span>
                      )}
                    </td>

                    {/* Review Status */}
                    <td className="py-3 px-3 text-[11px] text-stone-600">
                      <span className="capitalize">{item.review_status.toLowerCase().replace(/_/g, ' ')}</span>
                    </td>

                    {/* Age / Days Pending */}
                    <td className="py-3 px-3 font-mono text-[11px] text-stone-500">
                      {item.days_pending === 0 ? 'Today' : `${item.days_pending}d pending`}
                    </td>

                    {/* Action Button */}
                    <td className="py-3 px-3 text-right">
                      <Link
                        to={`/inspections/${item.inspection_id}`}
                        className="inline-block px-3 py-1 bg-emerald-900 hover:bg-emerald-800 text-white rounded text-xs font-semibold shadow-sm transition-colors"
                      >
                        Inspect →
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="py-12 text-center text-xs text-stone-500 bg-stone-50 rounded-lg border border-stone-200">
          No inspections match the selected review criteria.
        </div>
      )}
    </section>
  )
}
