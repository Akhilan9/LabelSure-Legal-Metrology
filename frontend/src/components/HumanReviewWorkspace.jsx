import React, { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function HumanReviewWorkspace({ inspection, user, refreshKey, onReviewUpdated }) {
  const [review, setReview] = useState(null)
  const [auditEvents, setAuditEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingAudit, setLoadingAudit] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState(null)

  // Rule Decisions editing state
  const [editingRuleKey, setEditingRuleKey] = useState(null)
  const [overrideVerdict, setOverrideVerdict] = useState('')
  const [overrideReason, setOverrideReason] = useState('')
  const [reviewerNotes, setReviewerNotes] = useState('')

  // Finalize / Reopen state
  const [showFinalizeModal, setShowFinalizeModal] = useState(false)
  const [finalComplianceStatus, setFinalComplianceStatus] = useState('COMPLIANT')
  const [summaryNotes, setSummaryNotes] = useState('')
  const [showReopenModal, setShowReopenModal] = useState(false)
  const [reopenReason, setReopenReason] = useState('')

  // Declaration Correction state
  const [showDeclModal, setShowDeclModal] = useState(false)
  const [selectedDeclType, setSelectedDeclType] = useState('MRP')
  const [declRawValue, setDeclRawValue] = useState('')
  const [declCorrectedValue, setDeclCorrectedValue] = useState('')
  const [declAction, setDeclAction] = useState('CORRECTED')
  const [declReason, setDeclReason] = useState('')

  const fetchReview = async () => {
    if (!inspection?.id) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get(`/inspections/${inspection.id}/review`)
      setReview(res.data)
    } catch (err) {
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load human review record')
      }
    } finally {
      setLoading(false)
    }
  }

  const fetchAudit = async () => {
    if (!inspection?.id) return
    setLoadingAudit(true)
    try {
      const res = await api.get(`/inspections/${inspection.id}/audit-trail`)
      setAuditEvents(res.data || [])
    } catch {
      // Non-fatal
    } finally {
      setLoadingAudit(false)
    }
  }

  useEffect(() => {
    fetchReview()
    fetchAudit()
  }, [inspection?.id, refreshKey])

  const isFinalized = review?.status === 'FINALIZED'
  const isSupervisor = false
  const isAdmin = user?.role === 'INSPECTOR'
  const canEdit = !isFinalized && !isSupervisor

  const handleSaveRuleDecision = async (ruleKey, ruleId, currentMachineVerdict) => {
    if (!overrideVerdict) return
    const isOverriding = overrideVerdict !== currentMachineVerdict
    if (isOverriding && (!overrideReason || overrideReason.trim().length < 5)) {
      setError('An override reason of at least 5 characters is mandatory when changing a machine verdict.')
      return
    }

    setSaving(true)
    setError(null)
    try {
      await api.post(`/inspections/${inspection.id}/review/rule-decisions`, {
        rule_id: ruleId || ruleKey,
        rule_key: ruleKey,
        final_verdict: overrideVerdict,
        override_reason: isOverriding ? overrideReason.trim() : null,
        reviewer_notes: reviewerNotes.trim() || null
      })
      setSuccessMessage(`Decision for ${ruleKey} recorded successfully.`)
      setEditingRuleKey(null)
      setOverrideReason('')
      setReviewerNotes('')
      await fetchReview()
      await fetchAudit()
      if (onReviewUpdated) onReviewUpdated()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to record rule decision')
    } finally {
      setSaving(false)
    }
  }

  const handleAddDeclarationCorrection = async (e) => {
    e.preventDefault()
    if (!declCorrectedValue.trim() || !declReason.trim()) {
      setError('Corrected value and justification reason are required.')
      return
    }

    setSaving(true)
    setError(null)
    try {
      await api.post(`/inspections/${inspection.id}/review/declaration-corrections`, {
        declaration_type: selectedDeclType,
        original_raw_value: declRawValue.trim() || null,
        original_normalized_value: null,
        corrected_value: declCorrectedValue.trim(),
        action: declAction,
        correction_reason: declReason.trim()
      })
      setSuccessMessage('Declaration correction saved.')
      setShowDeclModal(false)
      setDeclCorrectedValue('')
      setDeclRawValue('')
      setDeclReason('')
      await fetchReview()
      await fetchAudit()
      if (onReviewUpdated) onReviewUpdated()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to record declaration correction')
    } finally {
      setSaving(false)
    }
  }

  const handleFinalize = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await api.post(`/inspections/${inspection.id}/review/finalize`, {
        final_compliance_status: finalComplianceStatus,
        summary_notes: summaryNotes.trim() || null
      })
      setReview(res.data)
      setShowFinalizeModal(false)
      setSuccessMessage('Review finalized and locked. Chain of custody sealed.')
      await fetchAudit()
      if (onReviewUpdated) onReviewUpdated()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to finalize review')
    } finally {
      setSaving(false)
    }
  }

  const handleReopen = async () => {
    if (!reopenReason.trim() || reopenReason.trim().length < 5) {
      setError('A valid justification of at least 5 characters is mandatory to reopen a review.')
      return
    }

    setSaving(true)
    setError(null)
    try {
      const res = await api.post(`/inspections/${inspection.id}/review/reopen`, {
        reopen_reason: reopenReason.trim()
      })
      setReview(res.data)
      setShowReopenModal(false)
      setReopenReason('')
      setSuccessMessage('Inspection review reopened for authorized amendments.')
      await fetchAudit()
      if (onReviewUpdated) onReviewUpdated()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reopen review')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="bg-white border border-stone-300 rounded-lg shadow-sm p-6 mb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-stone-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-900 bg-emerald-100 px-2 py-0.5 rounded">
              Phase 10
            </span>
            <h2 className="text-base font-bold text-stone-900">
              Inspector Review, Overrides & Finalization
            </h2>
          </div>
          <p className="text-xs text-stone-500 mt-1">
            Human verification authority under Legal Metrology Act, 2009. Machine rules propose verdicts; authorized officers confirm or override with immutable justification.
          </p>
        </div>

        {/* Status badges & finalization controls */}
        <div className="flex items-center gap-3">
          {review && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-stone-500">Review Status:</span>
              <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
                review.status === 'FINALIZED'
                  ? 'bg-purple-100 text-purple-900 border-purple-300'
                  : review.status === 'REOPENED'
                  ? 'bg-amber-100 text-amber-900 border-amber-300'
                  : 'bg-blue-100 text-blue-900 border-blue-300'
              }`}>
                {review.status}
              </span>
              {review.final_compliance_status && (
                <span className={`text-xs px-2.5 py-1 rounded font-bold border ${
                  review.final_compliance_status === 'COMPLIANT'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : review.final_compliance_status === 'NON_COMPLIANT'
                    ? 'bg-rose-100 text-rose-800 border-rose-300'
                    : 'bg-amber-100 text-amber-800 border-amber-300'
                }`}>
                  {review.final_compliance_status}
                </span>
              )}
            </div>
          )}

          {canEdit && (
            <button
              type="button"
              onClick={() => setShowFinalizeModal(true)}
              className="px-3.5 py-1.5 text-xs font-bold text-white bg-emerald-900 hover:bg-emerald-800 rounded shadow transition-colors"
            >
              🔒 Finalize Review
            </button>
          )}

          {isFinalized && isAdmin && (
            <button
              type="button"
              onClick={() => setShowReopenModal(true)}
              className="px-3 py-1.5 text-xs font-bold text-amber-900 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded shadow-sm transition-colors"
            >
              🔓 Reopen Review (Admin)
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="my-4 p-3 bg-rose-50 border-l-4 border-rose-600 text-rose-900 text-xs rounded flex justify-between items-center">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="font-bold text-rose-950">✕</button>
        </div>
      )}
      {successMessage && (
        <div className="my-4 p-3 bg-emerald-50 border-l-4 border-emerald-600 text-emerald-900 text-xs rounded flex justify-between items-center">
          <span>{successMessage}</span>
          <button type="button" onClick={() => setSuccessMessage(null)} className="font-bold text-emerald-950">✕</button>
        </div>
      )}

      {/* Notice Banner */}
      {isFinalized && (
        <div className="my-4 p-3.5 bg-stone-100 border border-stone-300 rounded text-xs text-stone-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-stone-900 font-bold">🔒 Sealed Record:</span>
            <span>This inspection review was finalized on {review?.finalized_at ? new Date(review.finalized_at).toLocaleString() : 'N/A'}. All verdicts, corrections, and observations are permanently locked.</span>
          </div>
          {review?.summary_notes && (
            <span className="italic text-stone-600 ml-4 font-mono text-[11px]">Note: "{review.summary_notes}"</span>
          )}
        </div>
      )}

      {/* Grid of Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Left Column: Recorded Rule Overrides / Decisions */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-800">
              Rule Review Decisions ({review?.rule_decisions?.length || 0})
            </h3>
            <span className="text-[11px] text-stone-500">
              {review?.rule_decisions?.filter(d => d.is_overridden).length || 0} overridden
            </span>
          </div>

          {loading ? (
            <div className="p-4 text-center text-xs text-stone-500 animate-pulse">Loading review decisions…</div>
          ) : !review || review.rule_decisions.length === 0 ? (
            <div className="p-6 bg-stone-50 border border-dashed border-stone-300 rounded text-center text-xs text-stone-500">
              No rule decisions recorded yet. Evaluated rules can be reviewed directly in the Rule Compliance section or customized below.
            </div>
          ) : (
            <div className="space-y-3">
              {review.rule_decisions.map((dec) => (
                <div key={dec.id} className="p-3.5 border border-stone-200 rounded-lg bg-stone-50 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-stone-900">{dec.rule_key}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-stone-500">Machine:</span>
                      <span className="px-1.5 py-0.5 rounded bg-stone-200 text-stone-700 font-mono text-[10px]">
                        {dec.original_verdict}
                      </span>
                      <span className="text-stone-400">➔</span>
                      <span className="text-[10px] text-stone-500">Inspector:</span>
                      <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                        dec.final_verdict === 'PASS'
                          ? 'bg-emerald-100 text-emerald-800'
                          : dec.final_verdict === 'FAIL'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {dec.final_verdict}
                      </span>
                    </div>
                  </div>

                  {dec.is_overridden && (
                    <div className="p-2 bg-amber-50 border-l-2 border-amber-500 rounded text-[11px] text-amber-900">
                      <div className="font-semibold text-amber-950">Mandatory Override Justification:</div>
                      <p className="mt-0.5">{dec.override_reason}</p>
                    </div>
                  )}

                  {dec.reviewer_notes && (
                    <div className="text-[11px] text-stone-600 italic">
                      Notes: {dec.reviewer_notes}
                    </div>
                  )}

                  <div className="text-[10px] text-stone-400 flex justify-between items-center pt-1 border-t border-stone-200">
                    <span>Recorded: {new Date(dec.created_at).toLocaleTimeString()}</span>
                    {dec.is_overridden && (
                      <span className="text-amber-700 font-semibold">⚠️ Overridden by Inspector</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Declaration Corrections & Additions */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-800">
              Inspector Declaration Corrections ({review?.declaration_corrections?.length || 0})
            </h3>
            {canEdit && (
              <button
                type="button"
                onClick={() => setShowDeclModal(true)}
                className="px-2.5 py-1 text-[11px] font-bold text-emerald-900 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded transition-colors"
              >
                + Record Correction
              </button>
            )}
          </div>

          {loading ? (
            <div className="p-4 text-center text-xs text-stone-500 animate-pulse">Loading corrections…</div>
          ) : !review || review.declaration_corrections.length === 0 ? (
            <div className="p-6 bg-stone-50 border border-dashed border-stone-300 rounded text-center text-xs text-stone-500">
              No declaration corrections recorded. AI extractions remain unamended.
            </div>
          ) : (
            <div className="space-y-3">
              {review.declaration_corrections.map((corr) => (
                <div key={corr.id} className="p-3.5 border border-stone-200 rounded-lg bg-stone-50 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-stone-900">{corr.declaration_type}</span>
                    <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-blue-100 text-blue-900">
                      {corr.action}
                    </span>
                  </div>

                  {corr.original_raw_value && (
                    <div className="text-[11px] text-stone-500">
                      Original: <span className="line-through">{corr.original_raw_value}</span>
                    </div>
                  )}

                  <div className="text-[11px] text-stone-900 font-semibold">
                    Corrected Value: <span className="font-mono bg-white px-1.5 py-0.5 rounded border">{corr.corrected_value}</span>
                  </div>

                  <div className="p-2 bg-stone-100 rounded text-[11px] text-stone-700">
                    <span className="font-semibold text-stone-900">Reason:</span> {corr.correction_reason}
                  </div>

                  <div className="text-[10px] text-stone-400 text-right pt-1 border-t border-stone-200">
                    {new Date(corr.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modal: Record Declaration Correction */}
      {showDeclModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-lg max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="text-sm font-bold text-stone-900">Record Declaration Correction</h3>
              <button type="button" onClick={() => setShowDeclModal(false)} className="text-stone-400 hover:text-stone-600 font-bold">✕</button>
            </div>

            <form onSubmit={handleAddDeclarationCorrection} className="space-y-3 text-xs">
              <div>
                <label className="block text-stone-700 font-semibold mb-1">Declaration Type</label>
                <select
                  value={selectedDeclType}
                  onChange={(e) => setSelectedDeclType(e.target.value)}
                  className="w-full p-2 border border-stone-300 rounded bg-white"
                >
                  <option value="MRP">MRP (Maximum Retail Price)</option>
                  <option value="NET_QUANTITY">NET_QUANTITY (Net Content)</option>
                  <option value="MONTH_YEAR">MONTH_YEAR (Mfg / Pkd Date)</option>
                  <option value="CONSUMER_CARE_PHONE">CONSUMER_CARE_PHONE</option>
                  <option value="CONSUMER_CARE_EMAIL">CONSUMER_CARE_EMAIL</option>
                  <option value="MANUFACTURER_NAME">MANUFACTURER_NAME</option>
                  <option value="COUNTRY_OF_ORIGIN">COUNTRY_OF_ORIGIN</option>
                  <option value="BARCODE_OR_GTIN">BARCODE_OR_GTIN</option>
                </select>
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">Original Raw Text (Optional)</label>
                <input
                  type="text"
                  value={declRawValue}
                  onChange={(e) => setDeclRawValue(e.target.value)}
                  placeholder="e.g. MRP 120"
                  className="w-full p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">Corrected / Verified Value *</label>
                <input
                  type="text"
                  required
                  value={declCorrectedValue}
                  onChange={(e) => setDeclCorrectedValue(e.target.value)}
                  placeholder="e.g. INR 120.00 (Incl. of all taxes)"
                  className="w-full p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">Action Type</label>
                <select
                  value={declAction}
                  onChange={(e) => setDeclAction(e.target.value)}
                  className="w-full p-2 border border-stone-300 rounded bg-white"
                >
                  <option value="CORRECTED">CORRECTED (Amended AI reading)</option>
                  <option value="CONFIRMED">CONFIRMED (Inspector validated)</option>
                  <option value="REJECTED">REJECTED (Invalid / Hallucinated)</option>
                  <option value="MANUALLY_ADDED">MANUALLY_ADDED (Missing from OCR)</option>
                </select>
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">Justification Reason *</label>
                <textarea
                  required
                  rows={3}
                  value={declReason}
                  onChange={(e) => setDeclReason(e.target.value)}
                  placeholder="State the statutory or physical observation reason for this correction..."
                  className="w-full p-2 border border-stone-300 rounded"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowDeclModal(false)}
                  className="px-3 py-1.5 bg-stone-100 text-stone-700 rounded hover:bg-stone-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-1.5 bg-emerald-900 text-white font-bold rounded hover:bg-emerald-800"
                >
                  {saving ? 'Saving…' : 'Save Correction'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Finalize Review */}
      {showFinalizeModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="text-sm font-bold text-stone-900">🔒 Finalize Legal Metrology Review</h3>
              <button type="button" onClick={() => setShowFinalizeModal(false)} className="text-stone-400 hover:text-stone-600 font-bold">✕</button>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-900">
              <strong>Warning:</strong> Finalizing seals this inspection record into the immutable audit trail. No further edits or overrides will be permitted without Administrator approval.
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-stone-700 font-semibold mb-1">Final Compliance Determination *</label>
                <select
                  value={finalComplianceStatus}
                  onChange={(e) => setFinalComplianceStatus(e.target.value)}
                  className="w-full p-2 border border-stone-300 rounded bg-white font-bold"
                >
                  <option value="COMPLIANT">COMPLIANT (All mandatory statutory clauses satisfied)</option>
                  <option value="NON_COMPLIANT">NON_COMPLIANT (Statutory violation detected)</option>
                  <option value="CONDITIONAL_COMPLIANCE">CONDITIONAL_COMPLIANCE (Minor rectifyable defect)</option>
                  <option value="REJECTED">REJECTED (Inspection discarded / unreadable)</option>
                </select>
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">Summary Inspection Notes</label>
                <textarea
                  rows={4}
                  value={summaryNotes}
                  onChange={(e) => setSummaryNotes(e.target.value)}
                  placeholder="Provide closing inspector observations, recommended enforcement action, or statutory notices..."
                  className="w-full p-2 border border-stone-300 rounded"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t">
              <button
                type="button"
                onClick={() => setShowFinalizeModal(false)}
                className="px-3 py-1.5 bg-stone-100 text-stone-700 rounded hover:bg-stone-200 text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleFinalize}
                className="px-4 py-1.5 bg-emerald-900 text-white font-bold rounded hover:bg-emerald-800 text-xs"
              >
                {saving ? 'Finalizing…' : 'Confirm & Finalize'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Admin Reopen */}
      {showReopenModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="text-sm font-bold text-stone-900">🔓 Reopen Finalized Review</h3>
              <button type="button" onClick={() => setShowReopenModal(false)} className="text-stone-400 hover:text-stone-600 font-bold">✕</button>
            </div>

            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-900">
              <strong>Admin Authority:</strong> Reopening a finalized inspection unlocks it for inspector modification and logs a high-severity event in the Chain of Custody Audit Trail.
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-stone-700 font-semibold mb-1">Administrative Justification *</label>
                <textarea
                  required
                  rows={4}
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  placeholder="Detail the formal basis for reopening (e.g., Legal appeal filed, supplementary package photo provided)..."
                  className="w-full p-2 border border-stone-300 rounded"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t">
              <button
                type="button"
                onClick={() => setShowReopenModal(false)}
                className="px-3 py-1.5 bg-stone-100 text-stone-700 rounded hover:bg-stone-200 text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleReopen}
                className="px-4 py-1.5 bg-amber-700 text-white font-bold rounded hover:bg-amber-800 text-xs"
              >
                {saving ? 'Reopening…' : 'Authorize Reopen'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
