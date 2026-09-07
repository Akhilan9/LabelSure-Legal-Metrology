import React, { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function AuditTrailViewer({ inspection, refreshKey }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filterAction, setFilterAction] = useState('ALL')
  const [searchTerm, setSearchTerm] = useState('')

  const fetchAuditTrail = async () => {
    if (!inspection?.id) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get(`/inspections/${inspection.id}/audit-trail`)
      setEvents(res.data || [])
    } catch (err) {
      setError('Failed to fetch chain of custody audit events')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAuditTrail()
  }, [inspection?.id, refreshKey])

  const ACTION_BADGES = {
    REVIEW_CREATED: 'bg-blue-100 text-blue-900 border-blue-300',
    RULE_OVERRIDE: 'bg-amber-100 text-amber-900 border-amber-300 font-bold',
    RULE_DECISION_CONFIRMED: 'bg-emerald-100 text-emerald-900 border-emerald-300',
    DECLARATION_CORRECTED: 'bg-purple-100 text-purple-900 border-purple-300',
    OCR_CORRECTED: 'bg-indigo-100 text-indigo-900 border-indigo-300',
    REVIEW_FINALIZED: 'bg-emerald-900 text-white border-emerald-950 font-bold',
    REVIEW_REOPENED: 'bg-rose-100 text-rose-900 border-rose-300 font-bold',
  }

  const filteredEvents = events.filter((e) => {
    if (filterAction !== 'ALL' && e.action !== filterAction) return false
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase()
      return (
        e.action?.toLowerCase().includes(term) ||
        e.reason?.toLowerCase().includes(term) ||
        e.user_name?.toLowerCase().includes(term) ||
        e.entity_type?.toLowerCase().includes(term)
      )
    }
    return true
  })

  return (
    <section className="bg-white border border-stone-300 rounded-lg shadow-sm p-6 mb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-stone-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-700 bg-stone-100 px-2 py-0.5 rounded">
              Auditing
            </span>
            <h2 className="text-base font-bold text-stone-900">
              Chain of Custody & Audit Trail
            </h2>
          </div>
          <p className="text-xs text-stone-500 mt-1">
            Immutable chronological record of machine outputs, inspector decisions, statutory overrides, and administrative actions.
          </p>
        </div>

        {/* Filter controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <input
            type="text"
            placeholder="Search audit trail…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="text-xs px-2.5 py-1.5 border border-stone-300 rounded w-44"
          />
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="text-xs px-2.5 py-1.5 border border-stone-300 rounded bg-white"
          >
            <option value="ALL">All Event Types ({events.length})</option>
            <option value="RULE_OVERRIDE">Rule Overrides</option>
            <option value="DECLARATION_CORRECTED">Declaration Corrections</option>
            <option value="REVIEW_FINALIZED">Review Finalized</option>
            <option value="REVIEW_REOPENED">Review Reopened</option>
            <option value="REVIEW_CREATED">Review Created</option>
          </select>
          <button
            type="button"
            onClick={fetchAuditTrail}
            className="text-xs px-2.5 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 font-semibold rounded border"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="my-4 p-3 bg-rose-50 border border-rose-200 text-rose-900 text-xs rounded">
          {error}
        </div>
      )}

      {/* Events Timeline */}
      {loading ? (
        <div className="p-8 text-center text-xs text-stone-500 animate-pulse">Loading audit trail…</div>
      ) : filteredEvents.length === 0 ? (
        <div className="p-8 text-center text-xs text-stone-500 bg-stone-50 border border-dashed rounded mt-4">
          No audit events found matching filters.
        </div>
      ) : (
        <div className="relative border-l-2 border-stone-200 ml-4 mt-6 space-y-6">
          {filteredEvents.map((evt) => {
            const badgeStyle = ACTION_BADGES[evt.action] || 'bg-stone-100 text-stone-800 border-stone-300'
            return (
              <div key={evt.id} className="relative pl-6 text-xs group">
                {/* Timeline node */}
                <div className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-white border-2 border-stone-400 group-hover:border-emerald-700 transition-colors" />

                <div className="bg-stone-50 border border-stone-200 rounded-lg p-4 shadow-sm space-y-2 hover:border-stone-300 transition-colors">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded border ${badgeStyle}`}>
                        {evt.action}
                      </span>
                      <span className="font-bold text-stone-900">{evt.entity_type}</span>
                    </div>
                    <div className="text-[11px] text-stone-500 font-mono">
                      {new Date(evt.created_at).toLocaleString()}
                    </div>
                  </div>

                  {/* Actor Info */}
                  <div className="text-[11px] text-stone-600">
                    User: <strong>{evt.user_name || evt.user_id || 'System'}</strong>
                    {evt.ip_address && <span className="text-stone-400 ml-2">({evt.ip_address})</span>}
                  </div>

                  {/* Justification / Reason */}
                  {evt.reason && (
                    <div className="p-2 bg-white rounded border border-stone-200 text-[11px] text-stone-800">
                      <span className="font-semibold text-stone-900">Rationale / Note:</span> {evt.reason}
                    </div>
                  )}

                  {/* Diff / State Inspection if available */}
                  {(evt.before_state || evt.after_state) && (
                    <details className="mt-2 text-[10px] cursor-pointer">
                      <summary className="text-stone-500 hover:text-stone-700 font-semibold select-none">
                        View Event State Payload
                      </summary>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 p-2 bg-stone-900 text-stone-200 rounded font-mono text-[10px] overflow-x-auto">
                        <div>
                          <div className="text-stone-400 font-bold mb-1">Before State:</div>
                          <pre>{JSON.stringify(evt.before_state || {}, null, 2)}</pre>
                        </div>
                        <div>
                          <div className="text-emerald-400 font-bold mb-1">After State:</div>
                          <pre>{JSON.stringify(evt.after_state || {}, null, 2)}</pre>
                        </div>
                      </div>
                    </details>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
