import { useState } from 'react'
import AuthorizedImage from './AuthorizedImage'

const VERDICT_STYLES = {
  PASS: { badge: 'bg-emerald-100 text-emerald-900 border-emerald-300', text: 'text-emerald-700', label: 'COMPLIANT (PASS)' },
  FAIL: { badge: 'bg-rose-100 text-rose-900 border-rose-300', text: 'text-rose-700', label: 'NON-COMPLIANT (FAIL)' },
  UNCERTAIN: { badge: 'bg-amber-100 text-amber-900 border-amber-300', text: 'text-amber-700', label: 'UNCERTAIN (REVIEW REQUIRED)' },
  NOT_APPLICABLE: { badge: 'bg-stone-100 text-stone-700 border-stone-300', text: 'text-stone-500', label: 'NOT APPLICABLE' },
}

const STEP_ICONS = {
  PASSED: '✓',
  COMPLIANT: '✓',
  VIOLATION: '✗',
  NON_COMPLIANT: '✗',
  FAILED: '⚠️',
  CONFLICT: '⚡',
  UNCERTAIN: '❓',
  NEEDS_HUMAN_REVIEW: '🔍',
  NOT_APPLICABLE: '—',
}

const STEP_COLORS = {
  PASSED: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  COMPLIANT: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  VIOLATION: 'bg-rose-50 text-rose-800 border-rose-200',
  NON_COMPLIANT: 'bg-rose-50 text-rose-800 border-rose-200',
  FAILED: 'bg-amber-50 text-amber-800 border-amber-200',
  CONFLICT: 'bg-purple-50 text-purple-800 border-purple-200',
  UNCERTAIN: 'bg-amber-50 text-amber-800 border-amber-200',
  NEEDS_HUMAN_REVIEW: 'bg-amber-50 text-amber-800 border-amber-200',
  NOT_APPLICABLE: 'bg-stone-50 text-stone-600 border-stone-200',
}

export default function RuleLensModal({ explanation, onClose, onSelectImage }) {
  const [activeTab, setActiveTab] = useState('trace') // 'trace', 'evidence', 'legal', 'guidance'

  if (!explanation) return null

  const verdictStyle = VERDICT_STYLES[explanation.verdict] || VERDICT_STYLES.UNCERTAIN

  return (
    <div className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-3 sm:p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-white rounded-xl max-w-4xl w-full max-h-[92vh] overflow-hidden flex flex-col shadow-2xl border border-stone-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-stone-200 bg-stone-900 text-white flex justify-between items-start">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 px-2 py-0.5 rounded font-mono font-bold">
                RuleLens Explainability
              </span>
              <span className="text-xs font-mono text-stone-400">{explanation.rule_key}</span>
              {explanation.legal_status === 'PROTOTYPE_RULE' && (
                <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-400/30 px-1.5 py-0.5 rounded font-bold">
                  PROTOTYPE
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold font-serif text-stone-100">{explanation.title}</h3>
            <p className="text-xs text-stone-400">{explanation.legal_reference}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-auto px-2.5 py-1 bg-stone-800 hover:bg-stone-700 text-stone-300 rounded text-xs font-bold transition-colors"
          >
            ✕ Close
          </button>
        </div>

        {/* Verdict Bar */}
        <div className="p-3 bg-stone-100 border-b border-stone-200 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-stone-600 font-medium">Statutory Verdict:</span>
            <span className={`text-xs px-2.5 py-1 rounded font-bold border shadow-sm ${verdictStyle.badge}`}>
              {verdictStyle.label}
            </span>
            <span className="text-xs font-mono text-stone-500">[{explanation.reason_code}]</span>
          </div>
          <div className="text-xs text-stone-600">
            Severity: <strong className="uppercase">{explanation.severity}</strong> · Confidence:{' '}
            <strong>
              {explanation.evidence_confidence !== null && explanation.evidence_confidence !== undefined
                ? `${(explanation.evidence_confidence * 100).toFixed(0)}%`
                : 'N/A'}
            </strong>
          </div>
        </div>

        {/* Legal Disclaimer Banner */}
        <div className="px-4 py-2 bg-stone-50 border-b border-stone-200 text-[11px] text-stone-600 italic">
          ⚖️ {explanation.legal_disclaimer}
        </div>

        {/* Tabs */}
        <div className="flex border-b border-stone-200 bg-stone-50 px-4 text-xs font-semibold">
          {[
            ['trace', '🔍 Decision Trace Pipeline'],
            ['evidence', '📦 Evidence Provenance Map'],
            ['guidance', '💡 Counterfactual Guidance'],
            ['legal', '📜 Legal Precedents & Rules'],
          ].map(([tabKey, tabLabel]) => (
            <button
              key={tabKey}
              type="button"
              onClick={() => setActiveTab(tabKey)}
              className={`w-auto px-4 py-2.5 border-b-2 transition-colors ${
                activeTab === tabKey
                  ? 'border-emerald-700 text-emerald-900 bg-white'
                  : 'border-transparent text-stone-500 hover:text-stone-800'
              }`}
            >
              {tabLabel}
            </button>
          ))}
        </div>

        {/* Tab Body */}
        <div className="p-5 flex-1 overflow-y-auto space-y-4">
          {activeTab === 'trace' && (
            <div className="space-y-4">
              <div className="p-3 bg-stone-50 border border-stone-200 rounded text-xs text-stone-700">
                <strong>Explanation Summary:</strong> {explanation.explanation}
              </div>

              <h4 className="text-xs font-bold text-stone-800 uppercase tracking-wide">
                Step-by-Step Statutory Decision Pipeline
              </h4>

              <div className="space-y-3">
                {explanation.decision_trace.map((step) => {
                  const colorClass = STEP_COLORS[step.status] || STEP_COLORS.NOT_APPLICABLE
                  const icon = STEP_ICONS[step.status] || '•'
                  return (
                    <div key={step.step_number} className={`p-3.5 rounded-lg border flex gap-3 ${colorClass}`}>
                      <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center font-bold text-xs shadow-sm flex-shrink-0">
                        {icon}
                      </div>
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold">{step.title}</span>
                          <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-white/70">
                            {step.phase}
                          </span>
                        </div>
                        <p className="text-xs leading-relaxed">{step.detail}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-4">
              {/* Linked Candidates */}
              <div className="border border-stone-200 rounded-lg p-4 bg-white">
                <h4 className="text-xs font-bold text-stone-800 uppercase tracking-wide mb-2">
                  Extracted Declaration Candidates ({explanation.linked_evidence?.declarations?.length || 0})
                </h4>
                {explanation.linked_evidence?.declarations?.length === 0 ? (
                  <p className="text-xs text-stone-500 italic">No declaration candidate detected on package panels.</p>
                ) : (
                  <div className="space-y-2">
                    {explanation.linked_evidence.declarations.map((d) => (
                      <div key={d.id} className="p-3 bg-stone-50 rounded border border-stone-200 text-xs space-y-1">
                        <div className="flex justify-between">
                          <span className="font-semibold text-stone-900">{d.declaration_type}</span>
                          <span className="font-mono text-emerald-800 font-bold">
                            Score: {(d.confidence_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[11px] text-stone-600">
                          <div>Normalized Value: <strong>{d.normalized_value}</strong></div>
                          <div>Raw Text: <code className="bg-white px-1 rounded">{d.raw_value}</code></div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Linked Facts */}
              <div className="border border-stone-200 rounded-lg p-4 bg-white">
                <h4 className="text-xs font-bold text-stone-800 uppercase tracking-wide mb-2">
                  Context Facts ({explanation.linked_evidence?.facts?.length || 0})
                </h4>
                {explanation.linked_evidence?.facts?.length === 0 ? (
                  <p className="text-xs text-stone-500 italic">No specific context fact linked.</p>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-2">
                    {explanation.linked_evidence.facts.map((f) => (
                      <div key={f.id} className="p-2.5 bg-stone-50 rounded border border-stone-200 text-xs">
                        <div className="text-[10px] text-stone-500 font-mono">{f.fact_type}</div>
                        <div className="font-semibold text-stone-900 mt-0.5">{JSON.stringify(f.value)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Sufficiency Metrics */}
              <div className="border border-stone-200 rounded-lg p-4 bg-white text-xs space-y-2">
                <h4 className="font-bold text-stone-800 uppercase tracking-wide">
                  Photographic Sufficiency &amp; OCR Quality
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2 bg-stone-50 rounded border">
                    <div className="text-[10px] text-stone-500">Good Quality Images</div>
                    <div className="font-bold text-stone-900">{explanation.sufficiency_trace?.good_quality_images || 0} / {explanation.sufficiency_trace?.total_images || 0}</div>
                  </div>
                  <div className="p-2 bg-stone-50 rounded border">
                    <div className="text-[10px] text-stone-500">Successful OCR Runs</div>
                    <div className="font-bold text-stone-900">{explanation.sufficiency_trace?.successful_ocr_runs || 0}</div>
                  </div>
                  <div className="p-2 bg-stone-50 rounded border">
                    <div className="text-[10px] text-stone-500">Min OCR Threshold</div>
                    <div className="font-bold text-stone-900">{(explanation.sufficiency_trace?.min_ocr_confidence * 100).toFixed(0)}%</div>
                  </div>
                  <div className="p-2 bg-stone-50 rounded border">
                    <div className="text-[10px] text-stone-500">Absence Evaluation</div>
                    <div className="font-bold text-stone-900">{explanation.sufficiency_trace?.allows_absence_fail ? 'Permitted (Fail)' : 'Uncertain Only'}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'guidance' && (
            <div className="space-y-4">
              <div className="p-4 bg-emerald-50 border-l-4 border-emerald-700 rounded text-xs text-emerald-900 space-y-2">
                <h4 className="font-bold uppercase tracking-wide">Statutory Remediation Guidance</h4>
                <p className="leading-relaxed text-sm">{explanation.counterfactual_guidance}</p>
              </div>

              <div className="p-4 bg-stone-50 border border-stone-200 rounded text-xs text-stone-700 space-y-2">
                <h4 className="font-bold text-stone-900">Inspector Verification Options</h4>
                <ul className="list-disc list-inside space-y-1 text-stone-600">
                  <li>If declaration is present on an unphotographed panel, upload additional panel photos.</li>
                  <li>If OCR misread a blurry character, use the Human Review workspace to record an inspector correction.</li>
                  <li>If automated rule verdict is inaccurate, record an official statutory override with required audit justification.</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'legal' && (
            <div className="space-y-3 text-xs text-stone-700">
              <div className="p-4 bg-white border border-stone-200 rounded">
                <h4 className="font-bold text-stone-900 mb-1">Statutory Citation</h4>
                <p className="font-mono text-stone-800">{explanation.legal_reference}</p>
              </div>
              <div className="p-4 bg-white border border-stone-200 rounded">
                <h4 className="font-bold text-stone-900 mb-1">Rule Key &amp; Version</h4>
                <p className="font-mono text-stone-800">{explanation.rule_key} (v{explanation.rule_version})</p>
              </div>
              <div className="p-4 bg-white border border-stone-200 rounded">
                <h4 className="font-bold text-stone-900 mb-1">Enforcement Standard</h4>
                <p>Legal Metrology (Packaged Commodities) Rules, 2011 promulgated under the Legal Metrology Act, 2009 (Act No. 1 of 2010).</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-stone-100 border-t border-stone-200 flex justify-between items-center text-xs text-stone-600">
          <span className="font-mono text-[11px]">Rule ID: {explanation.rule_id}</span>
          <button
            type="button"
            onClick={onClose}
            className="w-auto px-4 py-1.5 bg-stone-800 hover:bg-stone-900 text-white rounded font-semibold text-xs"
          >
            Close RuleLens
          </button>
        </div>
      </div>
    </div>
  )
}
