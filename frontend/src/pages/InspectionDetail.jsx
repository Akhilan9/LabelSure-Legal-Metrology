import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import ContextApplicability from '../components/ContextApplicability'
import ExtractedDeclarations from '../components/ExtractedDeclarations'
import RuleComplianceEvaluation from '../components/RuleComplianceEvaluation'
import HumanReviewWorkspace from '../components/HumanReviewWorkspace'
import AuditTrailViewer from '../components/AuditTrailViewer'
import ReportExportPanel from '../components/ReportExportPanel'
import AuthorizedImage from '../components/AuthorizedImage'
import InspectionOCRSummarySection from '../components/InspectionOCRSummarySection'
import OCRBlockTable from '../components/OCRBlockTable'
import OCRBoundingBoxCanvas from '../components/OCRBoundingBoxCanvas'
import InspectionWorkflowStepper from '../components/InspectionWorkflowStepper'

const STATUS_BADGE_STYLES = {
  GOOD: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  ACCEPTABLE: 'bg-teal-100 text-teal-800 border-teal-300',
  POOR: 'bg-amber-100 text-amber-800 border-amber-300',
  UNREADABLE: 'bg-rose-100 text-rose-800 border-rose-300',
  PROCESSING_FAILED: 'bg-red-100 text-red-800 border-red-300',
  PENDING: 'bg-stone-100 text-stone-600 border-stone-300',
}

const FLAG_LABELS = {
  BLURRY: 'Blurry / Low Focus',
  TOO_DARK: 'Underexposed / Too Dark',
  TOO_BRIGHT: 'Overexposed / Too Bright',
  LOW_CONTRAST: 'Low Contrast',
  LOW_RESOLUTION: 'Low Resolution (minimum 800 × 600)',
  POSSIBLE_GLARE: 'Glare / Specular Reflection',
  INVALID_IMAGE: 'Corrupted / Invalid File',
  PROCESSING_ERROR: 'Pipeline Error',
}

export default function InspectionDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()

  const [contextRevision, setContextRevision] = useState(0)
  const [inspection, setInspection] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // OCR state
  const [ocrSummary, setOcrSummary] = useState(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [ocrRunsByImageId, setOcrRunsByImageId] = useState({})
  const [loadingImageOCR, setLoadingImageOCR] = useState(false)

  // Modal interaction
  const [selectedImage, setSelectedImage] = useState(null)
  const [activeViewMode, setActiveViewMode] = useState('ocr-boxes') // 'ocr-boxes', 'side-by-side', 'original', 'preprocessed'
  const [selectedBlockId, setSelectedBlockId] = useState(null)
  const [hoveredBlockId, setHoveredBlockId] = useState(null)
  const [showOverlays, setShowOverlays] = useState(true)
  const [showLabels, setShowLabels] = useState(true)

  // Actions
  const [submitting, setSubmitting] = useState(false)
  const [processingBatchQuality, setProcessingBatchQuality] = useState(false)
  const [processingBatchOCR, setProcessingBatchOCR] = useState(false)
  const [processingSingleQualityId, setProcessingSingleQualityId] = useState(null)
  const [processingSingleOCRId, setProcessingSingleOCRId] = useState(null)
  const [bannerMessage, setBannerMessage] = useState(location.state?.message || null)

  async function runAnalysis() {
    setProcessingBatchOCR(true); setError(null)
    try {
      const { data } = await api.post(`/inspections/${id}/analysis`, null, { timeout: 600000 })
      setBannerMessage(`Analysis complete: ${data.candidate_count} declarations. Review the linked findings below.`)
      setContextRevision(value => value + 1)
      await fetchInspection(); await fetchOCRSummary()
    } catch (e) { setError(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Analysis failed. Your uploaded photos remain saved; retry analysis.') }
    finally { setProcessingBatchOCR(false) }
  }

  const fetchInspection = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get(`/inspections/${id}`)
      setInspection(data)
    } catch (err) {
      setError(
        err.response?.status === 404
          ? 'Inspection not found or access restricted.'
          : 'Failed to load inspection details.'
      )
    } finally {
      setLoading(false)
    }
  }

  const fetchOCRSummary = async () => {
    setLoadingSummary(true)
    try {
      const { data } = await api.get(`/inspections/${id}/ocr/summary`)
      setOcrSummary(data)
    } catch {
      // Non-fatal if OCR has not been executed yet
    } finally {
      setLoadingSummary(false)
    }
  }

  const fetchImageOCR = async (imageId) => {
    setLoadingImageOCR(true)
    try {
      const { data } = await api.get(`/inspections/${id}/images/${imageId}/ocr`)
      setOcrRunsByImageId((prev) => ({ ...prev, [imageId]: data }))
    } catch {
      // No OCR run for image yet
      setOcrRunsByImageId((prev) => ({ ...prev, [imageId]: null }))
    } finally {
      setLoadingImageOCR(false)
    }
  }

  useEffect(() => {
    fetchInspection()
    fetchOCRSummary()
  }, [id])

  useEffect(() => {
    if (selectedImage) {
      fetchImageOCR(selectedImage.id)
    }
  }, [selectedImage?.id])

  const handleSubmit = async () => {
    if (!inspection) return
    setSubmitting(true)
    try {
      const { data } = await api.post(`/inspections/${inspection.id}/submit`)
      setInspection(data)
      setBannerMessage('Inspection submitted successfully! It is now locked and ready for regulatory analysis.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit inspection.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleProcessSingleQuality = async (imageId, force = false) => {
    setProcessingSingleQualityId(imageId)
    try {
      const { data } = await api.post(
        `/inspections/${id}/images/${imageId}/process${force ? '?force=true' : ''}`
      )
      setInspection((prev) => {
        if (!prev) return prev
        const updatedImages = prev.images.map((img) => {
          if (img.id === imageId) {
            return {
              ...img,
              quality_status: data.quality_status,
              width: data.width,
              height: data.height,
              processing_result: data,
            }
          }
          return img
        })
        return { ...prev, images: updatedImages }
      })

      if (selectedImage && selectedImage.id === imageId) {
        setSelectedImage((prev) => ({
          ...prev,
          quality_status: data.quality_status,
          width: data.width,
          height: data.height,
          processing_result: data,
        }))
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to assess image quality.')
    } finally {
      setProcessingSingleQualityId(null)
    }
  }

  const handleBatchProcessQuality = async (force = false) => {
    setProcessingBatchQuality(true)
    try {
      await api.post(`/inspections/${id}/process-images${force ? '?force=true' : ''}`)
      const { data } = await api.get(`/inspections/${id}`)
      setInspection(data)
      setBannerMessage('Image quality assessment and OpenCV preprocessing completed for all evidence images.')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to batch process images.')
    } finally {
      setProcessingBatchQuality(false)
    }
  }

  const handleProcessSingleOCR = async (imageId, force = false) => {
    setProcessingSingleOCRId(imageId)
    try {
      const { data } = await api.post(
        `/inspections/${id}/images/${imageId}/ocr${force ? '?force=true' : ''}`
      )
      setOcrRunsByImageId((prev) => ({ ...prev, [imageId]: data }))
      fetchOCRSummary()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to execute OCR on evidence image.')
    } finally {
      setProcessingSingleOCRId(null)
    }
  }

  const handleBatchProcessOCR = async (force = false) => {
    setProcessingBatchOCR(true)
    try {
      await api.post(`/inspections/${id}/ocr${force ? '?force=true' : ''}`)
      await fetchOCRSummary()
      if (selectedImage) {
        await fetchImageOCR(selectedImage.id)
      }
      setBannerMessage('OCR text recognition completed across all package panels.')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to execute batch OCR.')
    } finally {
      setProcessingBatchOCR(false)
    }
  }

  const handleOpenImageById = (imageId) => {
    const targetImg = inspection?.images.find((img) => img.id === imageId)
    if (targetImg) {
      setSelectedImage(targetImg)
      setActiveViewMode('ocr-boxes')
    }
  }

  const isEditable =
    inspection &&
    ['DRAFT', 'EVIDENCE_UPLOADED'].includes(inspection.status) &&
    ['INSPECTOR'].includes(user?.role)

  const canProcess =
    inspection &&
    ['INSPECTOR'].includes(user?.role)

  if (loading) {
    return (
      <main className="max-w-6xl mx-auto py-12 px-4 text-center text-xs text-stone-500">
        Loading inspection details…
      </main>
    )
  }

  if (error || !inspection) {
    return (
      <main className="max-w-4xl mx-auto py-12 px-4">
        <div className="bg-white border border-stone-300 rounded-lg p-8 text-center">
          <div className="text-3xl mb-2">⚠️</div>
          <h2 className="text-lg font-serif text-stone-900 font-bold mb-2">Unable to Open Inspection</h2>
          <p className="text-xs text-stone-600 mb-6">{error || 'Record could not be retrieved.'}</p>
          <Link to="/inspections" className="px-4 py-2 bg-stone-800 text-white rounded text-xs">
            ← Return to Inspections
          </Link>
        </div>
      </main>
    )
  }

  const activeImageOCR = selectedImage ? ocrRunsByImageId[selectedImage.id] : null
  const currentImageBlocks = activeImageOCR?.blocks || []

  const handleDownloadPdf = async () => {
    try {
      const response = await api.get(`/inspections/${id}/reports/pdf`, { responseType: 'blob' })
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = blobUrl
      link.setAttribute('download', `LabelSure_Statutory_Report_${inspection.inspection_code}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to download PDF report.')
    }
  }

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
      {/* Top Banner Notice */}
      {bannerMessage && (
        <div className="mb-6 p-4 bg-emerald-950 border border-emerald-800 text-emerald-200 text-xs rounded-xl flex justify-between items-center shadow-sm">
          <span>{bannerMessage}</span>
          <button
            type="button"
            onClick={() => setBannerMessage(null)}
            className="w-auto bg-transparent text-emerald-400 font-bold p-0"
          >
            ✕
          </button>
        </div>
      )}

      {/* Executive Direct End-Product Compliance Verdict Banner */}
      <div className={`mb-6 p-6 rounded-2xl border shadow-xl transition-all ${
        inspection.status === 'COMPLIANT'
          ? 'bg-gradient-to-r from-emerald-950 via-slate-900 to-emerald-900 border-emerald-500/50 text-white'
          : inspection.status === 'NON_COMPLIANT'
          ? 'bg-gradient-to-r from-rose-950 via-slate-900 to-rose-900 border-rose-500/50 text-white'
          : 'bg-gradient-to-r from-amber-950 via-slate-900 to-amber-900 border-amber-500/50 text-white'
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className={`px-4 py-1.5 rounded-full font-bold text-xs uppercase tracking-wider shadow ${
                inspection.status === 'COMPLIANT'
                  ? 'bg-emerald-500 text-slate-950'
                  : inspection.status === 'NON_COMPLIANT'
                  ? 'bg-rose-500 text-white'
                  : 'bg-amber-500 text-slate-950'
              }`}>
                {inspection.status === 'COMPLIANT' ? '✓ PASS — COMPLIANT' : inspection.status === 'NON_COMPLIANT' ? '✕ FAIL — NON-COMPLIANT' : '⚠ ATTENTION — REVIEW REQUIRED'}
              </span>
              <span className="text-xs text-slate-400 font-mono">LMPC Rules 2011-2026 Statutory Status</span>
            </div>
            <h2 className="text-2xl font-serif font-bold text-white">
              {inspection.inspection_code} · {inspection.product_name || 'Packaged Commodity'}
            </h2>
            <p className="text-xs text-slate-300">
              Automated Legal Metrology Pipeline Completed (OCR Panel Processing $\rightarrow$ Declaration Extraction $\rightarrow$ Rule Evaluation).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={handleDownloadPdf}
              className="w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-sm shadow-lg flex items-center gap-2 transition-all cursor-pointer"
            >
              <span>📄 Download Official PDF Report</span>
            </button>
            <button
              type="button"
              disabled={processingBatchOCR}
              onClick={runAnalysis}
              className="w-auto px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-slate-700 transition-colors"
            >
              {processingBatchOCR ? 'Running analysis…' : '⚡ Re-Run Auto-Analysis'}
            </button>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/inspections" className="text-xs text-emerald-400 hover:underline font-semibold">
              ← All Inspections
            </Link>
            <span className="text-slate-600">/</span>
            <span className="text-xs font-mono text-slate-400">{inspection.id.slice(0, 8)}…</span>
          </div>
          <div className="flex items-center gap-3 mt-2">
            <h1 className="text-2xl font-serif text-white font-bold">
              {inspection.inspection_code}
            </h1>
            <span
              className={`text-xs px-2.5 py-1 rounded font-semibold border ${
                inspection.status === 'COMPLIANT'
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                  : inspection.status === 'NON_COMPLIANT'
                  ? 'bg-rose-950 text-rose-300 border-rose-800'
                  : 'bg-slate-800 text-slate-300 border-slate-700'
              }`}
            >
              {inspection.status}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Created by <strong>{inspection.created_by_name || 'Inspector'}</strong> on{' '}
            {new Date(inspection.created_at).toLocaleString()}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {canProcess && inspection.images_count > 0 && (
            <>
              <button
                type="button"
                disabled={processingBatchOCR}
                onClick={runAnalysis}
                className="w-auto px-4 py-2 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl shadow flex items-center gap-1.5 transition-colors"
              >
                {processingBatchOCR ? 'Extracting Text…' : '⚡ Auto-Analyze Package'}
              </button>
              <button
                type="button"
                disabled={processingBatchQuality}
                onClick={() => handleBatchProcessQuality(false)}
                className="w-auto px-3 py-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl border border-slate-700 transition-colors"
              >
                {processingBatchQuality ? 'Analyzing Quality…' : 'Assess Image Quality'}
              </button>
            </>
          )}
          {isEditable && inspection.images_count > 0 && (
            <button
              type="button"
              disabled={submitting}
              onClick={handleSubmit}
              className="w-auto px-4 py-2 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow transition-colors"
            >
              {submitting ? 'Submitting…' : 'Submit & Analyze'}
            </button>
          )}
          {isEditable && (
            <button
              type="button"
              onClick={() => navigate(`/inspections/new?draft=${inspection.id}`)}
              className="w-auto px-3.5 py-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 font-medium"
            >
              + Add Evidence Photos
            </button>
          )}
        </div>
      </div>

      {/* 14-Step Guided Process Stepper Bar */}
      <div className="mt-6">
        <InspectionWorkflowStepper
          inspection={inspection}
          ocrSummary={ocrSummary}
          hasQuality={Boolean(inspection.images?.some(img => img.processing_result?.quality_status))}
          hasExtraction={Boolean(inspection.declarations_count > 0)}
          hasContext={Boolean(inspection.context_resolved)}
          hasEvaluation={Boolean(inspection.evaluations_count > 0)}
          hasReview={Boolean(inspection.review_status)}
          onRunQuality={() => handleBatchProcessQuality(false)}
          onRunOCR={() => handleBatchProcessOCR(false)}
          onExtract={() => runAnalysis()}
          onResolveContext={() => document.getElementById('context-section')?.scrollIntoView({ behavior: 'smooth' })}
          onEvaluateRules={() => document.getElementById('evaluation-section')?.scrollIntoView({ behavior: 'smooth' })}
          onOpenRuleLens={() => {
            if (inspection.images?.[0]) {
              setSelectedImage(inspection.images[0])
              setActiveViewMode('ocr-boxes')
            }
          }}
          onFinalize={() => document.getElementById('review-section')?.scrollIntoView({ behavior: 'smooth' })}
          onDownloadReport={() => document.getElementById('reports-section')?.scrollIntoView({ behavior: 'smooth' })}
          onGoDashboard={() => navigate('/dashboard')}
          onScrollToSection={(secId) => document.getElementById(secId)?.scrollIntoView({ behavior: 'smooth' })}
        />
      </div>

      <div id="evidence-section" className="grid grid-cols-1 lg:grid-cols-3 gap-6 my-8">
        {/* Left 2 Cols: Product & Photographic Evidence */}
        <div className="lg:col-span-2 space-y-6">
          {/* Product Specifications Card */}
          <section className="glass-panel border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">
              Product & Declaration Context
            </h2>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-xs">
              <div>
                <dt className="text-slate-400 font-medium">Product Name</dt>
                <dd className="font-semibold text-white mt-0.5 text-sm">{inspection.product_name || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400 font-medium">Brand Name</dt>
                <dd className="font-semibold text-white mt-0.5 text-sm">{inspection.brand_name || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400 font-medium">Product Category</dt>
                <dd className="text-slate-200 mt-0.5">{inspection.category || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400 font-medium">Package Type</dt>
                <dd className="text-slate-200 mt-0.5">{inspection.package_type || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400 font-medium">Import Status</dt>
                <dd className="text-slate-200 mt-0.5 font-mono">{inspection.import_status}</dd>
              </div>
              <div>
                <dt className="text-slate-400 font-medium">Barcode / GTIN</dt>
                <dd className="font-mono text-slate-200 mt-0.5">{inspection.barcode || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400 font-medium">Manufacturer</dt>
                <dd className="text-slate-200 mt-0.5">{inspection.manufacturer_name || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400 font-medium">Packer</dt>
                <dd className="text-slate-200 mt-0.5">{inspection.packer_name || '—'}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-slate-400 font-medium">Importer</dt>
                <dd className="text-slate-200 mt-0.5">{inspection.importer_name || '—'}</dd>
              </div>
              {inspection.notes && (
                <div className="sm:col-span-2 pt-2 border-t border-slate-800">
                  <dt className="text-slate-400 font-medium">Field Notes</dt>
                  <dd className="text-slate-200 mt-0.5 italic">{inspection.notes}</dd>
                </div>
              )}
            </dl>
          </section>

          {/* Evidence Gallery Card */}
          {/* Evidence Gallery Card */}
          <section className="glass-panel border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-2">
              <div>
                <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                  Photographic Evidence & Quality Status ({inspection.images_count})
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Click any image to view explainable OpenCV quality metrics and interactive OCR text extraction.
                </p>
              </div>
              {canProcess && inspection.images_count > 0 && (
                <button
                  type="button"
                  disabled={processingBatchQuality}
                  onClick={() => handleBatchProcessQuality(true)}
                  className="text-[11px] text-emerald-400 hover:underline font-semibold"
                >
                  Force Re-analyze All
                </button>
              )}
            </div>

            {inspection.images_count === 0 ? (
              <div className="text-center py-8 text-xs text-slate-400 bg-slate-900/60 rounded-xl border border-slate-800">
                No photographic evidence has been uploaded for this inspection record.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {inspection.images.map((img) => {
                  const proc = img.processing_result
                  const qStatus = proc ? proc.quality_status : 'PENDING'
                  const badgeClass = STATUS_BADGE_STYLES[qStatus] || STATUS_BADGE_STYLES.PENDING

                  return (
                    <div
                      key={img.id}
                      onClick={() => {
                        setSelectedImage(img)
                        setActiveViewMode('ocr-boxes')
                      }}
                      className="border border-slate-800 rounded-xl p-3 bg-slate-900/90 hover:border-emerald-500/50 hover:shadow-lg cursor-pointer transition-all flex flex-col justify-between group"
                    >
                      <div>
                        {/* Thumbnail */}
                        <div className="aspect-square bg-slate-950 rounded-lg overflow-hidden mb-2 relative">
                          <AuthorizedImage
                            src={img.content_url}
                            alt={img.original_filename}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                          />
                          {/* Overlay Tags */}
                          <div className="absolute top-1 left-1 flex flex-col gap-1">
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded font-bold border shadow-sm ${badgeClass}`}
                            >
                              {qStatus === 'PENDING' ? 'PENDING' : qStatus}
                            </span>
                          </div>
                          <span className="absolute bottom-1 right-1 bg-black/70 text-white text-[9px] px-1.5 py-0.5 rounded font-mono">
                            {(img.file_size / 1024).toFixed(0)} KB
                          </span>
                        </div>

                        {/* File Details */}
                        <div className="text-[11px] font-semibold text-slate-200 truncate" title={img.original_filename}>
                          {img.original_filename}
                        </div>

                        {/* Quality Flags Preview if any */}
                        {proc && proc.flags && proc.flags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {proc.flags.map((flag) => (
                              <span
                                key={flag}
                                className="text-[9px] px-1 py-0.2 bg-amber-950/80 text-amber-300 border border-amber-800 rounded font-medium truncate"
                              >
                                ⚠️ {FLAG_LABELS[flag] || flag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Card Footer */}
                      <div className="mt-3 pt-2 border-t border-slate-800 flex justify-between items-center text-[10px]">
                        <span className="font-semibold text-emerald-400 bg-emerald-950 border border-emerald-800/80 px-1.5 py-0.5 rounded">
                          {img.panel_type}
                        </span>
                        {proc ? (
                          <span className="text-slate-400 font-mono">
                            Focus: {proc.metrics?.blur_score?.toFixed(0) || '—'}
                          </span>
                        ) : (
                          <span className="text-slate-500 italic">Not analyzed</span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          {/* Phase 5 OCR Text Summary Across Panels */}
          <InspectionOCRSummarySection
            summary={ocrSummary}
            loading={loadingSummary}
            onTriggerBatchOCR={() => handleBatchProcessOCR(false)}
            onOpenImageModal={handleOpenImageById}
            canEdit={canProcess}
          />
        </div>

        {/* Right 1 Col: Pipeline Status & Audit Info */}
        <div className="space-y-6">
          {/* Analysis Pipeline Status */}
          <section className="glass-panel border border-slate-800 rounded-2xl p-5 shadow-xl">
            <h3 className="text-xs font-semibold text-white uppercase tracking-wide mb-3 border-b border-slate-800 pb-2">
              Compliance Pipeline Status
            </h3>

            {inspection.status === 'READY_FOR_ANALYSIS' ? (
              <div className="space-y-3">
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-900">
                  <div className="font-semibold mb-0.5">Ready for Analysis</div>
                  <p className="text-[11px] text-emerald-800">
                    Evidence is locked and OCR text extraction is available for Legal Metrology rule verification in subsequent phases.
                  </p>
                </div>
                <div className="text-xs text-stone-600 p-2.5 bg-stone-50 rounded border border-stone-200 space-y-1">
                  <div className="font-semibold text-stone-800">Pipeline Stages:</div>
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <span className="text-emerald-700">✓</span> <span>Evidence Ingestion</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <span className="text-emerald-700">✓</span> <span>Quality Assessment (OpenCV)</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <span className="text-emerald-700">✓</span> <span>OCR Text Extraction (PaddleOCR)</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-stone-400">
                    <span>○</span> <span>Statutory RuleLens Evaluation (Phase 6+)</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-stone-50 border border-stone-200 rounded text-xs text-stone-600">
                <div className="font-semibold text-stone-800 mb-1">Draft Stage Incomplete</div>
                <p className="text-[11px]">
                  Upload package panel photos and submit the inspection to queue it for automated Legal Metrology rule verification.
                </p>
              </div>
            )}
          </section>

          {/* Core Philosophy Notice */}
          <section className="bg-emerald-950 text-emerald-100 border border-emerald-900 rounded-lg p-5 shadow-sm text-xs space-y-2">
            <h3 className="font-semibold text-emerald-300 uppercase tracking-wide border-b border-emerald-800 pb-1.5 text-[11px]">
              APEX Architecture Mandate
            </h3>
            <p className="text-[11px] leading-relaxed italic text-emerald-200 font-serif">
              "AI OBSERVES. RULES DECIDE. EVIDENCE EXPLAINS. INSPECTORS VERIFY."
            </p>
            <p className="text-[10px] text-emerald-400 leading-normal">
              OCR models extract visible statutory declarations as evidence. They never make compliance determinations.
            </p>
          </section>

          {/* Quality Metrics Legend Card */}
          <section className="bg-white border border-stone-300 rounded-lg p-5 shadow-sm text-xs">
            <h3 className="font-semibold text-stone-700 uppercase tracking-wide mb-3 border-b pb-2">
              OpenCV Quality Standards
            </h3>
            <ul className="space-y-2 text-[11px] text-stone-600">
              <li className="flex items-start gap-1.5">
                <span className="font-bold text-stone-800">• Blur / Focus:</span>
                <span>Laplacian variance (≥100 = sharp edges for text extraction).</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-bold text-stone-800">• Brightness:</span>
                <span>Mean luminance [50–205] prevents dark underexposure and bleaching.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-bold text-stone-800">• Contrast:</span>
                <span>Std dev (≥30) ensures distinction between text and packaging.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-bold text-stone-800">• Glare / Flash:</span>
                <span>Near-white saturation (≤8% of pixels) prevents reflection flares.</span>
              </li>
            </ul>
          </section>

          {/* Custody and Audit Details */}
          <section className="bg-white border border-stone-300 rounded-lg p-5 shadow-sm text-xs">
            <h3 className="font-semibold text-stone-700 uppercase tracking-wide mb-3 border-b pb-2">
              Chain of Custody
            </h3>
            <dl className="space-y-2">
              <div>
                <dt className="text-stone-500">Inspection ID</dt>
                <dd className="font-mono text-stone-900 break-all">{inspection.id}</dd>
              </div>
              <div>
                <dt className="text-stone-500">Inspector ID</dt>
                <dd className="font-mono text-stone-900 break-all">{inspection.created_by_user_id}</dd>
              </div>
              <div>
                <dt className="text-stone-500">Created Timestamp</dt>
                <dd className="font-mono text-stone-900">{inspection.created_at}</dd>
              </div>
              <div>
                <dt className="text-stone-500">Submitted Timestamp</dt>
                <dd className="font-mono text-stone-900">{inspection.submitted_at || 'Not submitted'}</dd>
              </div>
            </dl>
          </section>
        </div>
      </div>

      <div id="extraction-section">
        <ExtractedDeclarations inspection={inspection} user={user} refreshKey={ocrSummary} onExtractionComplete={() => setContextRevision(v => v + 1)} />
      </div>
      <div id="context-section">
        <ContextApplicability inspection={inspection} user={user} refreshKey={contextRevision} ocrRefresh={ocrSummary} />
      </div>
      <div id="evaluation-section">
        <RuleComplianceEvaluation inspection={inspection} user={user} refreshKey={contextRevision} />
      </div>
      <div id="review-section">
        <HumanReviewWorkspace inspection={inspection} user={user} refreshKey={contextRevision} onReviewUpdated={() => setContextRevision(v => v + 1)} />
      </div>
      <div id="reports-section">
        <ReportExportPanel inspection={inspection} user={user} refreshKey={contextRevision} />
      </div>
      <div id="audit-section">
        <AuditTrailViewer inspection={inspection} refreshKey={contextRevision} />
      </div>

      {/* Detail & Interactive OCR / Preprocessing Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-3 sm:p-4 backdrop-blur-sm"
          onClick={() => setSelectedImage(null)}
        >
          <div
            className="bg-white rounded-lg max-w-6xl w-full max-h-[94vh] overflow-hidden flex flex-col shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-4 border-b border-stone-200 flex flex-wrap justify-between items-center bg-stone-100 gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-stone-900">{selectedImage.original_filename}</h4>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                      STATUS_BADGE_STYLES[selectedImage.processing_result?.quality_status || 'PENDING']
                    }`}
                  >
                    {selectedImage.processing_result?.quality_status || 'PENDING QUALITY'}
                  </span>
                  {activeImageOCR && (
                    <span className="text-[10px] bg-emerald-100 text-emerald-900 border border-emerald-300 px-2 py-0.5 rounded font-bold font-mono">
                      OCR: {activeImageOCR.block_count} Blocks
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-stone-500 flex gap-3 mt-1 font-mono">
                  <span>Panel: <strong>{selectedImage.panel_type}</strong></span>
                  <span>Dimensions: {selectedImage.width && selectedImage.height ? `${selectedImage.width}×${selectedImage.height} px` : '—'}</span>
                  <span>Size: {(selectedImage.file_size / 1024).toFixed(1)} KB</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {canProcess && (
                  <>
                    <button
                      type="button"
                      disabled={processingSingleOCRId === selectedImage.id}
                      onClick={() => handleProcessSingleOCR(selectedImage.id, true)}
                      className="w-auto px-3 py-1.5 bg-emerald-900 hover:bg-emerald-800 text-white rounded text-xs font-semibold flex items-center gap-1 shadow-sm"
                    >
                      {processingSingleOCRId === selectedImage.id ? 'Running OCR…' : '🔍 Run / Re-run OCR'}
                    </button>
                    <button
                      type="button"
                      disabled={processingSingleQualityId === selectedImage.id}
                      onClick={() => handleProcessSingleQuality(selectedImage.id, true)}
                      className="w-auto px-3 py-1.5 bg-stone-800 hover:bg-stone-900 text-white rounded text-xs font-semibold flex items-center gap-1"
                    >
                      {processingSingleQualityId === selectedImage.id ? 'Processing…' : '⚡ Re-assess Quality'}
                    </button>
                  </>
                )}
                <button
                  type="button"
                  onClick={() => setSelectedImage(null)}
                  className="w-auto px-3 py-1.5 bg-stone-200 hover:bg-stone-300 text-stone-800 rounded font-bold text-xs"
                >
                  ✕ Close
                </button>
              </div>
            </div>

            {/* Quality & OCR Metrics Sub-bar */}
            <div className="p-3 bg-stone-50 border-b border-stone-200 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                <div className="bg-white p-2 rounded border border-stone-200">
                  <div className="text-stone-500 text-[10px]">Blur Score</div>
                  <div className="font-mono font-bold text-stone-900 text-sm">
                    {selectedImage.processing_result?.metrics?.blur_score?.toFixed(1) ?? '—'}
                  </div>
                  <div className="text-[9px] text-stone-400">≥ 100.0 (Sharp)</div>
                </div>

                <div className="bg-white p-2 rounded border border-stone-200">
                  <div className="text-stone-500 text-[10px]">Brightness</div>
                  <div className="font-mono font-bold text-stone-900 text-sm">
                    {selectedImage.processing_result?.metrics?.brightness_score?.toFixed(1) ?? '—'}
                  </div>
                  <div className="text-[9px] text-stone-400">[50.0 – 205.0]</div>
                </div>

                <div className="bg-white p-2 rounded border border-stone-200">
                  <div className="text-stone-500 text-[10px]">Contrast</div>
                  <div className="font-mono font-bold text-stone-900 text-sm">
                    {selectedImage.processing_result?.metrics?.contrast_score?.toFixed(1) ?? '—'}
                  </div>
                  <div className="text-[9px] text-stone-400">≥ 30.0 (Std Dev)</div>
                </div>

                <div className="bg-white p-2 rounded border border-stone-200">
                  <div className="text-stone-500 text-[10px]">OCR Text Blocks</div>
                  <div className="font-mono font-bold text-stone-900 text-sm">
                    {activeImageOCR ? activeImageOCR.block_count : '—'}
                  </div>
                  <div className="text-[9px] text-stone-400">
                    {activeImageOCR?.status ? `Status: ${activeImageOCR.status}` : 'Not extracted'}
                  </div>
                </div>

                <div className="bg-white p-2 rounded border border-stone-200 col-span-2 sm:col-span-1">
                  <div className="text-stone-500 text-[10px]">Mean OCR Confidence</div>
                  <div className="font-mono font-bold text-emerald-900 text-sm">
                    {activeImageOCR?.average_confidence !== null && activeImageOCR?.average_confidence !== undefined
                      ? `${(activeImageOCR.average_confidence * 100).toFixed(1)}%`
                      : '—'}
                  </div>
                  <div className="text-[9px] text-stone-400">
                    Engine: {activeImageOCR?.engine_name || 'PaddleOCR'}
                  </div>
                </div>
              </div>
            </div>

            {/* View Mode Selector Tabs */}
            <div className="flex flex-wrap items-center justify-between border-b border-stone-200 bg-stone-100 px-4 pt-2 gap-2 text-xs">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setActiveViewMode('ocr-boxes')}
                  className={`w-auto px-3 py-1.5 rounded-t font-semibold transition-colors flex items-center gap-1.5 ${
                    activeViewMode === 'ocr-boxes'
                      ? 'bg-white text-emerald-950 border-t border-x border-stone-300'
                      : 'text-stone-600 hover:text-stone-900'
                  }`}
                >
                  <span>🔍 OCR Bounding Boxes ({currentImageBlocks.length})</span>
                </button>
                {selectedImage.processing_result?.derived_image_available && (
                  <button
                    type="button"
                    onClick={() => setActiveViewMode('side-by-side')}
                    className={`w-auto px-3 py-1.5 rounded-t font-semibold transition-colors ${
                      activeViewMode === 'side-by-side'
                        ? 'bg-white text-stone-900 border-t border-x border-stone-300'
                        : 'text-stone-600 hover:text-stone-900'
                    }`}
                  >
                    Side-by-Side Comparison
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setActiveViewMode('original')}
                  className={`w-auto px-3 py-1.5 rounded-t font-semibold transition-colors ${
                    activeViewMode === 'original'
                      ? 'bg-white text-stone-900 border-t border-x border-stone-300'
                      : 'text-stone-600 hover:text-stone-900'
                  }`}
                >
                  Raw Evidence
                </button>
                {selectedImage.processing_result?.derived_image_available && (
                  <button
                    type="button"
                    onClick={() => setActiveViewMode('preprocessed')}
                    className={`w-auto px-3 py-1.5 rounded-t font-semibold transition-colors ${
                      activeViewMode === 'preprocessed'
                        ? 'bg-white text-stone-900 border-t border-x border-stone-300'
                        : 'text-stone-600 hover:text-stone-900'
                    }`}
                  >
                    OCR-Ready Artifact
                  </button>
                )}
              </div>

              {/* Bounding Box View Controls */}
              {activeViewMode === 'ocr-boxes' && (
                <div className="flex items-center gap-3 pb-1 text-[11px] text-stone-600">
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showOverlays}
                      onChange={(e) => setShowOverlays(e.target.checked)}
                      className="rounded text-emerald-800"
                    />
                    <span>Polygons</span>
                  </label>
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showLabels}
                      onChange={(e) => setShowLabels(e.target.checked)}
                      className="rounded text-emerald-800"
                    />
                    <span>Reading Order Labels</span>
                  </label>
                </div>
              )}
            </div>

            {/* Modal Body Canvas / OCR Viewer Area */}
            <div className="p-4 flex-1 overflow-auto bg-stone-900/10 min-h-[400px]">
              {loadingImageOCR ? (
                <div className="h-full flex items-center justify-center text-xs text-stone-500 py-12">
                  Loading OCR evidence coordinates…
                </div>
              ) : activeViewMode === 'ocr-boxes' ? (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full">
                  {/* Canvas View (8 cols) */}
                  <div className="lg:col-span-7 flex flex-col items-center justify-center bg-white p-3 rounded-lg border border-stone-300 shadow-sm overflow-hidden min-h-[380px]">
                    <div className="text-[11px] font-semibold text-stone-700 mb-2 flex items-center justify-between w-full">
                      <span>
                        Target: {selectedImage.processing_result?.derived_image_available ? 'OCR-Ready Derived Artifact' : 'Original Evidence'}
                      </span>
                      <div className="flex items-center gap-2 text-[10px]">
                        <span className="flex items-center gap-1 font-semibold text-emerald-700">
                          <span className="w-2.5 h-2.5 rounded bg-emerald-500 inline-block"></span> GOOD (≥85%)
                        </span>
                        <span className="flex items-center gap-1 font-semibold text-amber-700">
                          <span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block"></span> REVIEW (60-84%)
                        </span>
                        <span className="flex items-center gap-1 font-semibold text-rose-700">
                          <span className="w-2.5 h-2.5 rounded bg-rose-500 inline-block"></span> LOW (&lt;60%)
                        </span>
                      </div>
                    </div>

                    <div className="flex-1 w-full flex items-center justify-center overflow-hidden">
                      <OCRBoundingBoxCanvas
                        imageUrl={
                          selectedImage.processing_result?.derived_image_available
                            ? selectedImage.processing_result.derived_content_url
                            : selectedImage.content_url
                        }
                        altText={selectedImage.original_filename}
                        blocks={currentImageBlocks}
                        selectedBlockId={selectedBlockId}
                        hoveredBlockId={hoveredBlockId}
                        onSelectBlock={(b) => setSelectedBlockId(b.id)}
                        onHoverBlock={(bId) => setHoveredBlockId(bId)}
                        showOverlays={showOverlays}
                        showLabels={showLabels}
                      />
                    </div>
                  </div>

                  {/* OCR Block List Table (5 cols) */}
                  <div className="lg:col-span-5 h-full flex flex-col">
                    <OCRBlockTable
                      blocks={currentImageBlocks}
                      selectedBlockId={selectedBlockId}
                      hoveredBlockId={hoveredBlockId}
                      onSelectBlock={(b) => setSelectedBlockId(b.id)}
                      onHoverBlock={(bId) => setHoveredBlockId(bId)}
                    />
                  </div>
                </div>
              ) : activeViewMode === 'side-by-side' && selectedImage.processing_result?.derived_image_available ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full h-full max-h-[55vh]">
                  <div className="flex flex-col items-center bg-white p-2 rounded border border-stone-300 shadow-sm overflow-hidden">
                    <span className="text-[11px] font-semibold text-stone-700 mb-1">
                      Raw Evidence Capture (Immutable)
                    </span>
                    <div className="flex-1 w-full flex items-center justify-center overflow-hidden">
                      <AuthorizedImage
                        src={selectedImage.content_url}
                        alt="Original"
                        className="max-h-[45vh] max-w-full object-contain"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col items-center bg-white p-2 rounded border border-stone-300 shadow-sm overflow-hidden">
                    <span className="text-[11px] font-semibold text-emerald-900 mb-1">
                      Derived Preprocessed Artifact (OCR-Ready PNG)
                    </span>
                    <div className="flex-1 w-full flex items-center justify-center overflow-hidden">
                      <AuthorizedImage
                        src={selectedImage.processing_result.derived_content_url}
                        alt="Preprocessed"
                        className="max-h-[45vh] max-w-full object-contain"
                      />
                    </div>
                  </div>
                </div>
              ) : activeViewMode === 'preprocessed' && selectedImage.processing_result?.derived_image_available ? (
                <div className="flex flex-col items-center justify-center">
                  <AuthorizedImage
                    src={selectedImage.processing_result.derived_content_url}
                    alt="Preprocessed"
                    className="max-h-[55vh] max-w-full object-contain rounded shadow bg-white p-1"
                  />
                  <span className="text-[10px] text-stone-500 mt-2 font-mono">
                    Derived SHA-256: {selectedImage.processing_result.derived_sha256}
                  </span>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center">
                  <AuthorizedImage
                    src={selectedImage.content_url}
                    alt={selectedImage.original_filename}
                    className="max-h-[55vh] max-w-full object-contain rounded shadow bg-white p-1"
                  />
                  <span className="text-[10px] text-stone-500 mt-2 font-mono">
                    Original SHA-256: {selectedImage.sha256}
                  </span>
                </div>
              )}
            </div>

            {/* Modal Footer Audit Metadata */}
            <div className="p-3 bg-stone-50 border-t border-stone-200 text-[10px] text-stone-600 font-mono flex flex-col sm:flex-row justify-between gap-2">
              <span className="truncate">Image ID: {selectedImage.id}</span>
              <span className="text-stone-400">Captured: {new Date(selectedImage.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
