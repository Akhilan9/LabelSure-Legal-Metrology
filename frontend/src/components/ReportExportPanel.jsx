import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function ReportExportPanel({ inspection, user, refreshKey }) {
  const [summary, setSummary] = useState(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [downloadingFormat, setDownloadingFormat] = useState(null)
  const [showJsonModal, setShowJsonModal] = useState(false)
  const [jsonContent, setJsonContent] = useState(null)
  const [loadingJson, setLoadingJson] = useState(false)
  const [copiedHash, setCopiedHash] = useState(false)

  const fetchSummary = async () => {
    if (!inspection?.id) return
    setLoadingSummary(true)
    try {
      const { data } = await api.get(`/inspections/${inspection.id}/reports/summary`)
      setSummary(data)
    } catch {
      // Non-fatal if evaluations/reviews not yet present
      setSummary(null)
    } finally {
      setLoadingSummary(false)
    }
  }

  useEffect(() => {
    fetchSummary()
  }, [inspection?.id, refreshKey])

  const downloadFile = async (url, filename, formatLabel) => {
    setDownloadingFormat(formatLabel)
    try {
      const response = await api.get(url, { responseType: 'blob' })
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = blobUrl
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      alert(err.response?.data?.detail || `Failed to download ${formatLabel} report.`)
    } finally {
      setDownloadingFormat(null)
    }
  }

  const handleDownloadPdf = () => {
    const filename = `LabelSure_Statutory_Report_${inspection.inspection_code}.pdf`
    downloadFile(`/inspections/${inspection.id}/reports/pdf`, filename, 'PDF')
  }

  const handleDownloadRulesCsv = () => {
    const filename = `LabelSure_Violations_${inspection.inspection_code}.csv`
    downloadFile(`/inspections/${inspection.id}/reports/csv?target=rules`, filename, 'Rules CSV')
  }

  const handleDownloadDeclarationsCsv = () => {
    const filename = `LabelSure_Declarations_${inspection.inspection_code}.csv`
    downloadFile(`/inspections/${inspection.id}/reports/csv?target=declarations`, filename, 'Declarations CSV')
  }

  const handleOpenJsonModal = async () => {
    setShowJsonModal(true)
    setLoadingJson(true)
    try {
      const { data } = await api.get(`/inspections/${inspection.id}/reports/json`)
      setJsonContent(data)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to fetch JSON snapshot.')
      setShowJsonModal(false)
    } finally {
      setLoadingJson(false)
    }
  }

  const copyTamperHash = () => {
    if (summary?.tamper_sha256) {
      navigator.clipboard.writeText(summary.tamper_sha256)
      setCopiedHash(true)
      setTimeout(() => setCopiedHash(false), 2000)
    }
  }

  return (
    <section className="bg-white border border-stone-300 rounded-lg p-6 shadow-sm my-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4 border-b border-stone-200 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-stone-900 uppercase tracking-wide font-serif">
              Phase 11 · Statutory Reports & Evidentiary Exports
            </span>
            {summary?.is_finalized && (
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded border border-emerald-300">
                LOCKED & FINALIZED
              </span>
            )}
          </div>
          <p className="text-xs text-stone-500 mt-0.5">
            Tamper-evident legal exports conforming to Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchSummary}
            disabled={loadingSummary}
            className="w-auto px-3 py-1 bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs rounded border border-stone-300 font-medium"
          >
            {loadingSummary ? 'Refreshing…' : '↻ Refresh Status'}
          </button>
        </div>
      </div>

      {loadingSummary && !summary ? (
        <div className="py-6 text-center text-xs text-stone-500">
          Generating cryptographic report digest…
        </div>
      ) : summary ? (
        <>
          {/* PASS/FAIL Banner */}
          <div className="mb-6 p-4 rounded-lg text-center font-bold">
            {summary.overall_compliance === 'COMPLIANT' && (
              <div className="bg-emerald-50 text-emerald-800 text-5xl">
                ✓ PASS
              </div>
            )}
            {summary.overall_compliance === 'NON_COMPLIANT' && (
              <div className="bg-rose-50 text-rose-800 text-5xl">
                ✗ FAIL
              </div>
            )}
            {summary.overall_compliance === null || summary.overall_compliance === 'UNCERTAIN' && (
              <div className="bg-amber-50 text-amber-800 text-5xl">
                ⚠ UNDECIDED
              </div>
            )}
          </div>

          {/* Executive Compliance & Cryptographic Seal Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-stone-50 p-4 rounded-lg border border-stone-200 text-xs">
            <div className="p-3 bg-white rounded border border-stone-200">
              <div className="text-[10px] text-stone-500 font-semibold uppercase">Overall Compliance</div>
              <div className="mt-1 flex items-center gap-1.5">
                <span
                  className={`px-2 py-0.5 rounded font-bold text-xs ${
                    summary.overall_compliance === 'COMPLIANT'
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : summary.overall_compliance === 'NON_COMPLIANT'
                      ? 'bg-rose-100 text-rose-800 border border-rose-300'
                      : 'bg-amber-100 text-amber-800 border border-amber-300'
                  }`}
                >
                  {summary.overall_compliance}
                </span>
              </div>
            </div>

            <div className="p-3 bg-white rounded border border-stone-200">
              <div className="text-[10px] text-stone-500 font-semibold uppercase">Rule Scorecard</div>
              <div className="mt-1 flex items-center gap-2 font-mono text-[11px]">
                <span className="text-emerald-700 font-bold">{summary.pass_count} Pass</span>
                <span className="text-stone-300">|</span>
                <span className="text-rose-700 font-bold">{summary.violations_count} Fail</span>
                <span className="text-stone-300">|</span>
                <span className="text-amber-700 font-bold">{summary.uncertain_count} Uncertain</span>
              </div>
            </div>

            <div className="p-3 bg-white rounded border border-stone-200">
              <div className="text-[10px] text-stone-500 font-semibold uppercase">Human Overrides</div>
              <div className="mt-1 font-mono font-bold text-stone-800">
                {summary.overrides_count > 0 ? (
                  <span className="text-amber-700">⚠️ {summary.overrides_count} Overridden</span>
                ) : (
                  <span className="text-emerald-700">0 Overrides (Automated AST Consensus)</span>
                )}
              </div>
            </div>

            <div className="p-3 bg-white rounded border border-stone-200">
              <div className="text-[10px] text-stone-500 font-semibold uppercase">Review Custody</div>
              <div className="mt-1 text-stone-800 truncate" title={summary.reviewer_name || summary.generated_by}>
                {summary.reviewer_name ? `Verified: ${summary.reviewer_name}` : `Gen: ${summary.generated_by}`}
              </div>
            </div>
          </div>

          {/* Tamper-Evident Cryptographic SHA-256 Seal */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-emerald-950 text-emerald-100 rounded-lg text-xs font-mono">
            <div className="flex items-center gap-2 truncate">
              <span className="text-emerald-400 font-bold">🔒 SHA-256 HASH:</span>
              <span className="text-emerald-200 truncate">{summary.tamper_sha256}</span>
            </div>
            <button
              type="button"
              onClick={copyTamperHash}
              className="w-auto shrink-0 px-2.5 py-1 bg-emerald-800 hover:bg-emerald-700 text-white rounded text-[11px] font-sans font-semibold transition-colors"
            >
              {copiedHash ? '✓ Copied!' : 'Copy Hash'}
            </button>
          </div>

          {/* Export Action Buttons Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={handleDownloadPdf}
              className="p-3 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg shadow-sm text-left transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-emerald-100">
                  <span>📄 Inspection PDF Report</span>
                  <span className="text-[10px] bg-emerald-800 px-1.5 py-0.5 rounded font-mono">A4</span>
                </div>
                <p className="text-[11px] text-emerald-200 mt-1 leading-tight">
                  Findings, legal references and evidence photos with integrity hashes.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-emerald-300 group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
                {downloadingFormat === 'PDF' ? 'Generating PDF…' : '⬇ Download PDF →'}
              </span>
            </button>

            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={handleDownloadRulesCsv}
              className="p-3 bg-stone-800 hover:bg-stone-900 text-white rounded-lg shadow-sm text-left transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-stone-100">
                  <span>📊 Rule Violations CSV</span>
                  <span className="text-[10px] bg-stone-700 px-1.5 py-0.5 rounded font-mono">CSV</span>
                </div>
                <p className="text-[11px] text-stone-300 mt-1 leading-tight">
                  Formula-injection sanitized spreadsheet export of all rule verdicts and rationales.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-stone-300 group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
                {downloadingFormat === 'Rules CSV' ? 'Exporting CSV…' : '⬇ Export CSV →'}
              </span>
            </button>

            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={handleDownloadDeclarationsCsv}
              className="p-3 bg-stone-800 hover:bg-stone-900 text-white rounded-lg shadow-sm text-left transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-stone-100">
                  <span>📑 Declarations Ledger CSV</span>
                  <span className="text-[10px] bg-stone-700 px-1.5 py-0.5 rounded font-mono">CSV</span>
                </div>
                <p className="text-[11px] text-stone-300 mt-1 leading-tight">
                  Complete candidate extraction ledger with raw OCR values, confidence & review status.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-stone-300 group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
                {downloadingFormat === 'Declarations CSV' ? 'Exporting CSV…' : '⬇ Export CSV →'}
              </span>
            </button>

            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={handleOpenJsonModal}
              className="p-3 bg-stone-700 hover:bg-stone-800 text-white rounded-lg shadow-sm text-left transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-stone-100">
                  <span>🔍 Canonical JSON Snapshot</span>
                  <span className="text-[10px] bg-stone-600 px-1.5 py-0.5 rounded font-mono">JSON</span>
                </div>
                <p className="text-[11px] text-stone-300 mt-1 leading-tight">
                  Cryptographically normalized JSON payload with immutable evidence provenance.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-stone-300 group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
                View / Export JSON →
              </span>
            </button>
          </div>
        </>
      ) : (
        <div className="py-6 text-center text-xs text-stone-500 bg-stone-50 rounded border border-stone-200">
          Run OCR extraction and RuleLens evaluation above to generate evidentiary compliance reports.
        </div>
      )}

      {/* Canonical JSON Modal */}
      {showJsonModal && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
          onClick={() => setShowJsonModal(false)}
        >
          <div
            className="bg-white rounded-lg max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-stone-200 flex justify-between items-center bg-stone-100">
              <div>
                <h4 className="text-sm font-bold text-stone-900 font-mono">
                  Canonical JSON Snapshot · {inspection.inspection_code}
                </h4>
                <p className="text-[11px] text-stone-500 font-mono">
                  Tamper Hash: {summary?.tamper_sha256}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(jsonContent, null, 2)], { type: 'application/json' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `LabelSure_Snapshot_${inspection.inspection_code}.json`
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                  className="w-auto px-3 py-1 bg-stone-800 hover:bg-stone-900 text-white rounded text-xs font-semibold"
                >
                  ⬇ Download JSON
                </button>
                <button
                  type="button"
                  onClick={() => setShowJsonModal(false)}
                  className="w-auto px-3 py-1 bg-stone-200 hover:bg-stone-300 text-stone-800 rounded text-xs font-bold"
                >
                  ✕ Close
                </button>
              </div>
            </div>

            <div className="p-4 flex-1 overflow-auto bg-stone-900 text-emerald-400 font-mono text-[11px]">
              {loadingJson ? (
                <div className="text-center py-8 text-stone-400">Loading canonical JSON payload…</div>
              ) : (
                <pre className="whitespace-pre-wrap">{JSON.stringify(jsonContent, null, 2)}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
