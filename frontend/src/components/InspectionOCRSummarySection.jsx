import { useState } from 'react'

const PANEL_NAMES = {
  PRINCIPAL_DISPLAY_PANEL: 'Principal Display Panel (PDP)',
  FRONT_PANEL: 'Front Panel',
  BACK_PANEL: 'Back Panel / Declarations',
  SIDE_PANEL_LEFT: 'Left Side Panel',
  SIDE_PANEL_RIGHT: 'Right Side Panel',
  TOP_PANEL: 'Top Lid / Flap',
  BOTTOM_PANEL: 'Bottom / Base Panel',
  INGREDIENTS_PANEL: 'Ingredients Statement',
  NUTRITION_FACTS: 'Nutritional Information',
  MRP_PANEL: 'MRP & Date Coding Area',
  MANUFACTURER_INFO: 'Manufacturer / Packer Address',
  OTHER: 'Supplementary Panel',
}

export default function InspectionOCRSummarySection({
  summary,
  loading = false,
  onTriggerBatchOCR,
  onOpenImageModal,
  canEdit = false,
}) {
  const [activePanelIdx, setActivePanelIdx] = useState(0)
  const [copiedPanel, setCopiedPanel] = useState(false)
  const [copiedAll, setCopiedAll] = useState(false)

  if (loading) {
    return (
      <div className="bg-white border border-stone-300 rounded-lg p-6 text-center text-xs text-stone-500 shadow-sm">
        Loading OCR evidence summary…
      </div>
    )
  }

  if (!summary || summary.total_images === 0) {
    return (
      <div className="bg-white border border-stone-300 rounded-lg p-6 text-center shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900 uppercase tracking-wider mb-2">
          OCR Extracted Evidence Text
        </h3>
        <p className="text-xs text-stone-500 mb-4">
          No photographic evidence available for OCR text recognition.
        </p>
      </div>
    )
  }

  const panels = summary.panels || []
  const currentPanel = panels[activePanelIdx] || panels[0]

  const handleCopyPanel = () => {
    if (!currentPanel || !currentPanel.text_lines) return
    navigator.clipboard.writeText(currentPanel.text_lines.join('\n'))
    setCopiedPanel(true)
    setTimeout(() => setCopiedPanel(false), 2000)
  }

  const handleCopyAll = () => {
    const allLines = []
    panels.forEach((p) => {
      if (p.text_lines && p.text_lines.length > 0) {
        allLines.push(`--- [${p.panel_type}] ---`)
        allLines.push(...p.text_lines)
        allLines.push('')
      }
    })
    navigator.clipboard.writeText(allLines.join('\n'))
    setCopiedAll(true)
    setTimeout(() => setCopiedAll(false), 2000)
  }

  return (
    <section className="bg-white border border-stone-300 rounded-lg p-6 shadow-sm space-y-6">
      {/* Header & High-Level Metrics */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-stone-900 uppercase tracking-wider">
              Extracted Package Evidence Text (OCR Observation)
            </h2>
            <span className="text-[10px] bg-stone-100 text-stone-700 px-2 py-0.5 rounded font-mono border">
              Phase 5 Active
            </span>
          </div>
          <p className="text-[11px] text-stone-500 mt-0.5">
            Deterministic and deep learning text recognition across all package panels for regulatory verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              type="button"
              onClick={onTriggerBatchOCR}
              className="w-auto px-3.5 py-1.5 bg-emerald-900 hover:bg-emerald-800 text-white rounded text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors"
            >
              <span>🔍 Run OCR on All Panels</span>
            </button>
          )}
          <button
            type="button"
            onClick={handleCopyAll}
            className="w-auto px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-800 border border-stone-300 rounded text-xs font-medium transition-colors"
          >
            {copiedAll ? '✓ Copied All Panels' : '📋 Copy All Panels'}
          </button>
        </div>
      </div>

      {/* Aggregate Scorecards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-stone-50 border border-stone-200 rounded">
          <div className="text-[10px] text-stone-500 font-medium">Evidence Panels</div>
          <div className="text-lg font-bold font-mono text-stone-900 mt-0.5">
            {summary.ocr_completed_count} / {summary.total_images}
          </div>
          <div className="text-[9px] text-stone-400">Completed OCR</div>
        </div>

        <div className="p-3 bg-stone-50 border border-stone-200 rounded">
          <div className="text-[10px] text-stone-500 font-medium">Total Text Blocks</div>
          <div className="text-lg font-bold font-mono text-stone-900 mt-0.5">
            {summary.total_ocr_blocks}
          </div>
          <div className="text-[9px] text-stone-400">Extracted lines / polygons</div>
        </div>

        <div className="p-3 bg-stone-50 border border-stone-200 rounded">
          <div className="text-[10px] text-stone-500 font-medium">Mean OCR Confidence</div>
          <div className="text-lg font-bold font-mono text-emerald-900 mt-0.5">
            {summary.average_confidence !== null && summary.average_confidence !== undefined
              ? `${(summary.average_confidence * 100).toFixed(1)}%`
              : '—'}
          </div>
          <div className="text-[9px] text-stone-400">Across all blocks</div>
        </div>

        <div className="p-3 bg-stone-50 border border-stone-200 rounded">
          <div className="text-[10px] text-stone-500 font-medium">Preprocessing Linkage</div>
          <div className="text-lg font-bold font-mono text-stone-900 mt-0.5">
            {summary.images_processed} / {summary.total_images}
          </div>
          <div className="text-[9px] text-stone-400">Phase 4 OCR-ready inputs</div>
        </div>
      </div>

      {/* Panel Selector Tabs */}
      {panels.length > 0 && (
        <div className="border border-stone-200 rounded-lg overflow-hidden">
          <div className="flex border-b border-stone-200 bg-stone-100 overflow-x-auto text-xs">
            {panels.map((p, idx) => {
              const isActive = activePanelIdx === idx
              const hasText = p.text_lines && p.text_lines.length > 0

              return (
                <button
                  key={p.image_id || idx}
                  type="button"
                  onClick={() => setActivePanelIdx(idx)}
                  className={`w-auto px-4 py-2.5 font-semibold text-left whitespace-nowrap transition-colors border-r border-stone-200 flex items-center gap-2 ${
                    isActive
                      ? 'bg-white text-emerald-950 border-b-2 border-b-emerald-800'
                      : 'text-stone-600 hover:bg-stone-200/60'
                  }`}
                >
                  <span>{PANEL_NAMES[p.panel_type] || p.panel_type}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                      hasText
                        ? 'bg-emerald-100 text-emerald-900'
                        : 'bg-stone-200 text-stone-500'
                    }`}
                  >
                    {p.block_count}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Active Panel Content Area */}
          {currentPanel && (
            <div className="p-4 bg-white text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-stone-200">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-stone-800">
                    {PANEL_NAMES[currentPanel.panel_type] || currentPanel.panel_type}
                  </span>
                  {currentPanel.average_confidence !== null && (
                    <span className="text-[10px] bg-emerald-50 text-emerald-900 border border-emerald-200 px-2 py-0.5 rounded font-mono font-bold">
                      Avg Conf: {(currentPanel.average_confidence * 100).toFixed(1)}%
                    </span>
                  )}
                  {currentPanel.status && (
                    <span className="text-[9px] bg-stone-100 text-stone-700 px-1.5 py-0.5 rounded font-mono">
                      Status: {currentPanel.status}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {currentPanel.image_id && (
                    <button
                      type="button"
                      onClick={() => onOpenImageModal?.(currentPanel.image_id)}
                      className="w-auto px-2.5 py-1 text-[11px] bg-stone-100 hover:bg-stone-200 text-stone-800 border rounded font-medium transition-colors"
                    >
                      🖼️ View Image & Bounding Boxes
                    </button>
                  )}
                  {currentPanel.text_lines && currentPanel.text_lines.length > 0 && (
                    <button
                      type="button"
                      onClick={handleCopyPanel}
                      className="w-auto px-2.5 py-1 text-[11px] bg-stone-800 hover:bg-stone-900 text-white rounded font-medium transition-colors"
                    >
                      {copiedPanel ? '✓ Copied' : '📋 Copy Panel Text'}
                    </button>
                  )}
                </div>
              </div>

              {/* Text Lines Card */}
              {currentPanel.text_lines && currentPanel.text_lines.length > 0 ? (
                <div className="bg-stone-900 text-stone-100 rounded-lg p-4 font-mono text-[11px] leading-relaxed max-h-[300px] overflow-y-auto shadow-inner space-y-1">
                  {currentPanel.text_lines.map((line, lineIdx) => (
                    <div key={lineIdx} className="flex items-start gap-2 hover:bg-stone-800/80 px-1 py-0.5 rounded">
                      <span className="text-stone-500 select-none min-w-[24px] text-right font-bold">
                        {lineIdx + 1}.
                      </span>
                      <span className="text-emerald-300 font-medium select-text break-words">
                        {line}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-stone-400 italic bg-stone-50 rounded border border-dashed border-stone-300">
                  {currentPanel.ocr_run_id
                    ? 'No text detected on this panel.'
                    : 'OCR has not been run for this panel image yet.'}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
