import { useEffect, useState } from 'react'
import { api } from '../api/client'
import RuleLensModal from './RuleLensModal'

const VERDICT_STYLES = {
  PASS: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  FAIL: 'bg-rose-100 text-rose-900 border-rose-300',
  UNCERTAIN: 'bg-amber-100 text-amber-900 border-amber-300',
  NOT_APPLICABLE: 'bg-stone-100 text-stone-700 border-stone-300',
}

const SEVERITY_STYLES = {
  CRITICAL: 'bg-rose-100 text-rose-800 border-rose-200',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
  MEDIUM: 'bg-amber-100 text-amber-800 border-amber-200',
  LOW: 'bg-blue-100 text-blue-800 border-blue-200',
  INFO: 'bg-stone-100 text-stone-700 border-stone-200',
}

export default function RuleComplianceEvaluation({ inspection, user, refreshKey, onEvaluationComplete }) {
  const [summary, setSummary] = useState(null)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState(null)
  const [allowPrototypes, setAllowPrototypes] = useState(true)

  // Explainability Modal
  const [selectedExplanation, setSelectedExplanation] = useState(null)
  const [loadingExplanation, setLoadingExplanation] = useState(false)

  const base = `/inspections/${inspection.id}`
  const canEvaluate = ['INSPECTOR'].includes(user?.role)

  const fetchEvaluation = async () => {
    setLoading(true)
    setError(null)
    try {
      const summaryRes = await api.get(`${base}/evaluation`)
      setSummary(summaryRes.data)
      const resultsRes = await api.get(`${base}/evaluation/results`)
      setResults(resultsRes.data)
    } catch {
      // Non-fatal if no evaluation run exists yet
      setSummary(null)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEvaluation()
  }, [inspection.id, refreshKey])

  const handleEvaluate = async () => {
    setEvaluating(true)
    setError(null)
    try {
      const { data } = await api.post(`${base}/evaluate`, {
        allow_prototype_rules: allowPrototypes,
      })
      setSummary(data)
      const resultsRes = await api.get(`${base}/evaluation/results`)
      setResults(resultsRes.data)
      if (onEvaluationComplete) onEvaluationComplete()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to execute rule evaluation.')
    } finally {
      setEvaluating(false)
    }
  }

  const handleOpenRuleLens = async (ruleKey) => {
    setLoadingExplanation(true)
    try {
      const { data } = await api.get(`${base}/rules/${ruleKey}/explanation`)
      setSelectedExplanation(data)
    } catch (err) {
      alert(err.response?.data?.detail || 'Unable to generate RuleLens explanation.')
    } finally {
      setLoadingExplanation(false)
    }
  }

  return (
    <section className="bg-white border border-stone-300 rounded-lg p-6 shadow-sm my-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold font-serif text-stone-900">
              Legal Metrology Statutory Rule Evaluation
            </h2>
            <span className="text-[10px] bg-emerald-100 text-emerald-900 border border-emerald-300 px-2 py-0.5 rounded font-bold">
              Phase 8 Engine
            </span>
          </div>
          <p className="text-xs text-stone-500 mt-1">
            Deterministic statutory verification against the Legal Metrology (Packaged Commodities) Rules, 2011.
          </p>
        </div>

        {/* Evaluate Action Button */}
        {canEvaluate && (
          <div className="flex flex-col sm:flex-row items-end sm:items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-stone-700 cursor-pointer">
              <input
                type="checkbox"
                checked={allowPrototypes}
                onChange={(e) => setAllowPrototypes(e.target.checked)}
                className="rounded text-emerald-800"
              />
              <span>Allow Prototype Rules</span>
            </label>
            <button
              type="button"
              disabled={evaluating}
              onClick={handleEvaluate}
              className="w-auto px-4 py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded text-xs font-bold shadow flex items-center gap-1.5 transition-colors"
            >
              {evaluating ? 'Evaluating Rules…' : '⚡ Run Statutory Verification'}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-900 text-xs rounded">
          ⚠️ {error}
        </div>
      )}

      {/* Summary KPI Cards */}
      {summary ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg">
              <div className="text-[10px] uppercase font-bold text-stone-500">Overall Verdict</div>
              <div className="mt-1">
                <span
                  className={`text-xs px-2.5 py-1 rounded font-bold border inline-block ${
                    VERDICT_STYLES[summary.overall] || VERDICT_STYLES.NOT_APPLICABLE
                  }`}
                >
                  {summary.overall}
                </span>
              </div>
            </div>

            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div className="text-[10px] uppercase font-bold text-emerald-700">Passed (Compliant)</div>
              <div className="text-xl font-bold font-mono text-emerald-900 mt-0.5">
                {summary.pass_count}
              </div>
            </div>

            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg">
              <div className="text-[10px] uppercase font-bold text-rose-700">Violations (Fail)</div>
              <div className="text-xl font-bold font-mono text-rose-900 mt-0.5">
                {summary.fail_count}
              </div>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="text-[10px] uppercase font-bold text-amber-700">Uncertain (Review)</div>
              <div className="text-xl font-bold font-mono text-amber-900 mt-0.5">
                {summary.uncertain_count}
              </div>
            </div>

            <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg">
              <div className="text-[10px] uppercase font-bold text-stone-600">Not Applicable</div>
              <div className="text-xl font-bold font-mono text-stone-800 mt-0.5">
                {summary.not_applicable_count}
              </div>
            </div>
          </div>

          {/* Prototype disclaimer */}
          {summary.prototype && (
            <div className="p-3 bg-amber-50 border-l-4 border-amber-500 text-amber-900 text-xs rounded space-y-0.5">
              <div className="font-bold">⚠️ Research Prototype Rules Active</div>
              <p className="text-[11px] text-amber-800">
                Evaluation includes prototype statutory rules. Results provide preliminary automated analysis for judicial &amp; inspector audit review.
              </p>
            </div>
          )}

          {/* Execution metadata bar */}
          <div className="flex flex-wrap items-center justify-between text-[11px] text-stone-500 bg-stone-50 p-2.5 rounded border border-stone-200 font-mono">
            <span>Ruleset: <strong>{summary.ruleset_id} (v{summary.ruleset_version})</strong></span>
            <span>Engine: <strong>v{summary.engine_version}</strong></span>
            <span>Evaluated: {new Date(summary.completed_at).toLocaleString()}</span>
            <span>Snapshot SHA: {summary.snapshot_sha256?.slice(0, 10)}…</span>
          </div>

          {/* Rule Results List */}
          <div className="space-y-3 mt-4">
            <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider">
              Statutory Declarations Verification Matrix ({results.length})
            </h3>

            {results.map((r) => {
              const vStyle = VERDICT_STYLES[r.verdict] || VERDICT_STYLES.NOT_APPLICABLE
              const sStyle = SEVERITY_STYLES[r.severity] || SEVERITY_STYLES.INFO

              return (
                <div
                  key={r.id}
                  className="border border-stone-200 rounded-lg p-4 bg-stone-50 hover:bg-white hover:border-emerald-700 hover:shadow-sm transition-all space-y-2"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs px-2.5 py-0.5 rounded font-bold border ${vStyle}`}>
                        {r.verdict}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border uppercase ${sStyle}`}>
                        {r.severity}
                      </span>
                      <h4 className="text-xs font-bold text-stone-900">{r.title}</h4>
                      <span className="text-[10px] font-mono text-stone-400">({r.rule_key})</span>
                    </div>

                    <button
                      type="button"
                      disabled={loadingExplanation}
                      onClick={() => handleOpenRuleLens(r.rule_key)}
                      className="w-auto px-3 py-1 text-xs bg-emerald-950 hover:bg-emerald-900 text-white rounded font-semibold flex items-center gap-1 shadow-sm transition-colors self-start sm:self-auto"
                    >
                      <span>🔍 RuleLens™ Explain</span>
                    </button>
                  </div>

                  <p className="text-xs text-stone-700 leading-relaxed">{r.explanation}</p>

                  <div className="flex flex-wrap items-center justify-between text-[11px] text-stone-500 pt-1 border-t border-stone-200 gap-2">
                    <span className="italic">{r.legal_reference}</span>
                    <div className="flex items-center gap-3 font-mono">
                      <span>Reason: <strong>{r.reason_code}</strong></span>
                      {r.evidence_confidence !== null && (
                        <span>Confidence: <strong>{(r.evidence_confidence * 100).toFixed(0)}%</strong></span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-xs text-stone-500 bg-stone-50 rounded border border-stone-200 space-y-2">
          <p>No rule evaluation has been executed for this inspection snapshot yet.</p>
          {canEvaluate && (
            <p className="text-stone-600">
              Ensure context has been resolved, then click <strong>"Run Statutory Verification"</strong> to evaluate all statutory rules.
            </p>
          )}
        </div>
      )}

      {/* RuleLens Explanation Modal */}
      {selectedExplanation && (
        <RuleLensModal
          explanation={selectedExplanation}
          onClose={() => setSelectedExplanation(null)}
        />
      )}
    </section>
  )
}
