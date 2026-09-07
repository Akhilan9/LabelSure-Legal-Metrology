import { useState } from 'react'

export const WORKFLOW_STEPS = [
  { id: 1, key: 'login', label: 'Login', desc: 'Authenticated inspector session established.' },
  { id: 2, key: 'create', label: 'Create inspection', desc: 'Inspection initialized with product metadata.' },
  { id: 3, key: 'upload', label: 'Upload images', desc: 'Package photos captured via webcam or file upload.' },
  { id: 4, key: 'thumbnails', label: 'View thumbnails', desc: 'Inspect evidence photo thumbnails and orientation.' },
  { id: 5, key: 'quality', label: 'Run quality processing', desc: 'Assess Laplacian blur, contrast, brightness & resolution.' },
  { id: 6, key: 'ocr', label: 'Run OCR', desc: 'Execute PaddleOCR to extract text blocks & relative coordinates.' },
  { id: 7, key: 'extract', label: 'Extract declarations', desc: 'Run deterministic parser for the 12 Rule 6 declarations.' },
  { id: 8, key: 'context', label: 'Resolve context', desc: 'Resolve package category applicability & contextual facts.' },
  { id: 9, key: 'evaluate', label: 'Evaluate rules', desc: 'Evaluate version-aware LMPC legal rulesets (2011-2026).' },
  { id: 10, key: 'rulelens', label: 'Open RuleLens', desc: 'Inspect 2-way visual linkage connecting rules to bounding boxes.' },
  { id: 11, key: 'review', label: 'Perform review/override', desc: 'Apply officer overrides with mandatory comment audit trail.' },
  { id: 12, key: 'finalize', label: 'Finalize inspection', desc: 'Lock inspection findings and finalize review verdict.' },
  { id: 13, key: 'report', label: 'Generate/download report', desc: 'Compile court-admissible ReportLab PDF Compliance Certificate.' },
  { id: 14, key: 'dashboard', label: 'View dashboard/history', desc: 'View analytics KPI dashboard and full adjudication audit log.' },
]

export default function InspectionWorkflowStepper({
  inspection,
  ocrSummary,
  hasQuality,
  hasExtraction,
  hasContext,
  hasEvaluation,
  hasReview,
  onRunQuality,
  onRunOCR,
  onExtract,
  onResolveContext,
  onEvaluateRules,
  onOpenRuleLens,
  onFinalize,
  onDownloadReport,
  onGoDashboard,
  onScrollToSection,
}) {
  const [expanded, setExpanded] = useState(true)

  // Determine current active step index (1-14)
  const calculateCurrentStep = () => {
    if (!inspection) return 1
    if (!inspection.images || inspection.images.length === 0) return 3
    if (!hasQuality) return 5
    if (!ocrSummary || ocrSummary.total_blocks_count === 0) return 6
    if (!hasExtraction) return 7
    if (!hasContext) return 8
    if (!hasEvaluation) return 9
    if (!hasReview) return 11
    if (inspection.status !== 'FINALIZED' && inspection.status !== 'SUBMITTED') return 12
    return 13
  }

  const currentStepId = calculateCurrentStep()

  const isStepCompleted = (stepId) => {
    if (stepId <= 2) return true
    if (stepId === 3 || stepId === 4) return inspection?.images_count > 0
    if (stepId === 5) return hasQuality
    if (stepId === 6) return ocrSummary?.total_blocks_count > 0
    if (stepId === 7) return hasExtraction
    if (stepId === 8) return hasContext
    if (stepId === 9) return hasEvaluation
    if (stepId === 10) return hasEvaluation
    if (stepId === 11) return hasReview
    if (stepId === 12) return inspection?.status === 'FINALIZED' || inspection?.status === 'SUBMITTED'
    if (stepId === 13) return inspection?.status === 'FINALIZED' || inspection?.status === 'SUBMITTED'
    if (stepId === 14) return false
    return false
  }

  const currentStepObj = WORKFLOW_STEPS.find((s) => s.id === currentStepId) || WORKFLOW_STEPS[0]

  const handleExecuteAction = (stepId) => {
    switch (stepId) {
      case 3:
      case 4:
        onScrollToSection?.('evidence-section')
        break
      case 5:
        onRunQuality?.()
        break
      case 6:
        onRunOCR?.()
        break
      case 7:
        onExtract?.()
        break
      case 8:
        onResolveContext?.()
        onScrollToSection?.('context-section')
        break
      case 9:
        onEvaluateRules?.()
        onScrollToSection?.('evaluation-section')
        break
      case 10:
        onOpenRuleLens?.()
        break
      case 11:
        onScrollToSection?.('review-section')
        break
      case 12:
        onFinalize?.()
        break
      case 13:
        onDownloadReport?.()
        break
      case 14:
        onGoDashboard?.()
        break
      default:
        break
    }
  }

  return (
    <aside aria-label="Step-by-step Guided Process" className="mb-8 border border-emerald-800/30 rounded-xl bg-gradient-to-br from-stone-900 via-stone-900 to-emerald-950 text-white p-5 shadow-xl">
      {/* Top Bar with Title and Current Step Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-stone-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-white shadow">
            {currentStepObj.id}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                Step-by-step Guided Process
              </span>
              <span className="text-xs text-stone-400">({currentStepObj.id} of 14)</span>
            </div>
            <h3 className="text-lg font-serif font-bold text-white">{currentStepObj.label}</h3>
            <p className="text-xs text-stone-300">{currentStepObj.desc}</p>
          </div>
        </div>

        {/* 1-Click Direct Action Button for Current Step */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => handleExecuteAction(currentStepObj.id)}
            className="w-auto px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-stone-950 font-bold text-xs rounded-lg shadow-lg hover:shadow-emerald-500/20 transition-all flex items-center gap-2"
          >
            <span>▶ Execute Step {currentStepObj.id}: {currentStepObj.label}</span>
          </button>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="w-auto px-3 py-2 bg-stone-800 hover:bg-stone-700 text-stone-300 text-xs rounded border border-stone-700"
          >
            {expanded ? 'Hide Steps ▲' : 'Show All 14 Steps ▼'}
          </button>
        </div>
      </div>

      {/* 14-Step Process Visual Stepper Bar */}
      {expanded && (
        <div className="mt-4 pt-2">
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 lg:grid-cols-14 gap-2">
            {WORKFLOW_STEPS.map((step) => {
              const completed = isStepCompleted(step.id)
              const isActive = step.id === currentStepId

              return (
                <button
                  key={step.id}
                  type="button"
                  onClick={() => {
                    handleExecuteAction(step.id)
                  }}
                  title={`Step ${step.id}: ${step.label} — ${step.desc}`}
                  className={`flex flex-col items-center p-2 rounded-lg text-center transition-all border ${
                    isActive
                      ? 'bg-emerald-900/80 border-emerald-400 text-white shadow-md ring-2 ring-emerald-400/40'
                      : completed
                      ? 'bg-stone-800/80 border-emerald-900/60 text-emerald-300 hover:bg-stone-800'
                      : 'bg-stone-900/60 border-stone-800 text-stone-400 hover:bg-stone-800/40'
                  }`}
                >
                  <span
                    className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center mb-1 ${
                      isActive
                        ? 'bg-emerald-400 text-stone-950'
                        : completed
                        ? 'bg-emerald-900 text-emerald-300'
                        : 'bg-stone-800 text-stone-500'
                    }`}
                  >
                    {completed ? '✓' : step.id}
                  </span>
                  <span className="text-[10px] font-medium line-clamp-2 leading-tight">
                    {step.label}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </aside>
  )
}
