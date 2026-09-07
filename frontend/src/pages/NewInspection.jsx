import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { scanNotice, validatePhotos } from '../api/scan'
import WebcamModal from '../components/WebcamModal'
import AuthorizedImage from '../components/AuthorizedImage'

const MANDATORY_DECLARATIONS = [
  { type: 'COMMON_PRODUCT_NAME', label: 'Generic / Common Commodity Name' },
  { type: 'NET_QUANTITY', label: 'Net Quantity (Magnitude & Unit)' },
  { type: 'MAXIMUM_RETAIL_PRICE', label: 'Maximum Retail Price (MRP)' },
  { type: 'UNIT_SALE_PRICE', label: 'Unit Sale Price (USP)' },
  { type: 'MONTH_YEAR_PACKAGING', label: 'Month & Year of Packaging / Import' },
  { type: 'EXPIRY_BEST_BEFORE', label: 'Expiry / Best Before Date' },
  { type: 'MANUFACTURER_ADDRESS', label: 'Manufacturer Name & Address' },
  { type: 'PACKER_ADDRESS', label: 'Packer / Importer Name & Address' },
  { type: 'COUNTRY_OF_ORIGIN', label: 'Country of Origin' },
  { type: 'CONSUMER_CARE', label: 'Consumer Care Details' },
  { type: 'DIMENSIONS', label: 'Dimensions & Size' },
  { type: 'ECOMMERCE_DECLARATION', label: 'E-Commerce Specific Declarations' },
]

const PANELS = ['FRONT', 'BACK', 'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'DECLARATION_PANEL', 'MRP_PANEL', 'OTHER']
const button = 'w-auto px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-sm shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed'
const secondary = 'w-auto px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-sm transition-colors disabled:opacity-50'
const message = e => typeof e.response?.data?.detail === 'string' ? e.response.data.detail : e.message || 'Something went wrong. Please try again.'

export default function NewInspection() {
  const navigate = useNavigate()
  const [search, setSearch] = useSearchParams()
  const draftId = search.get('draft')
  const [restoring, setRestoring] = useState(Boolean(draftId))
  const [inspection, setInspection] = useState(null)
  const [cameraOpen, setCameraOpen] = useState(search.get('camera') === '1')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [step, setStep] = useState(1)
  const [busy, setBusy] = useState('')
  const lock = useRef(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [dragging, setDragging] = useState(false)
  const [form, setForm] = useState({})
  const [candidates, setCandidates] = useState([])
  const [scanned, setScanned] = useState(false)
  const uploadInput = useRef(null)
  const cameraInput = useRef(null)
  const images = inspection?.images || []

  useEffect(() => {
    if (!draftId || inspection?.id === draftId) { setRestoring(false); return }
    const controller = new AbortController()
    setRestoring(true)
    api.get(`/inspections/${draftId}`, { signal: controller.signal }).then(({ data }) => {
      if (!['DRAFT', 'EVIDENCE_UPLOADED'].includes(data.status)) { navigate(`/inspections/${data.id}`, { replace: true }); return }
      setInspection(data)
    }).catch(e => { if (!controller.signal.aborted) setError(message(e)) })
      .finally(() => { if (!controller.signal.aborted) setRestoring(false) })
    return () => controller.abort()
  }, [draftId])

  async function operation(label, task) {
    if (lock.current || restoring || (draftId && !inspection)) return
    lock.current = true
    setBusy(label); setError(''); setNotice('')
    try { await task() } catch (e) { setError(message(e)) }
    finally { lock.current = false; setBusy('') }
  }

  async function refresh(id) {
    const { data } = await api.get(`/inspections/${id}`)
    setInspection(data)
    return data
  }

  async function scan(id) {
    setScanned(false); setCandidates([])
    setBusy('Scanning package text… This can take a few minutes on the first scan.')
    const { data: batch } = await api.post(`/inspections/${id}/ocr`, null, { timeout: 600000 })
    const warning = scanNotice(batch)
    setBusy('Extracting product details…')
    await api.post(`/inspections/${id}/extract-declarations`, null, { timeout: 60000 })
    const { data: declarations } = await api.get(`/inspections/${id}/declarations?limit=1000`)
    await refresh(id)
    setCandidates(declarations)
    setScanned(true)
    setNotice(warning || (declarations.length ? 'Scan complete. Review extracted details.' : 'Text was scanned, but no supported details were identified.'))
    setStep(2)
  }

  async function invalidateAutofill(id) {
    setScanned(false); setCandidates([])
  }

  function selectFiles(list, panel) {
    const files = Array.from(list || [])
    if (!files.length) return
    operation('Uploading photos…', async () => {
      validatePhotos(files, images.length)
      let current = inspection
      if (!current) {
        const { data } = await api.post('/inspections', { product_name: 'Scanning package' })
        current = data
        setInspection(data)
        setSearch({ draft: data.id }, { replace: true })
      }
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      const panels = files.map(() => panel || 'FRONT')
      panels.forEach(p => formData.append('panel_types', p))

      const { data: uploaded } = await api.post(`/inspections/${current.id}/images`, formData, {
        onUploadProgress: (evt) => {
          if (evt.total) setUploadProgress(Math.round((evt.loaded * 100) / evt.total))
        }
      })
      setUploadProgress(0)
      await invalidateAutofill(current.id)
      await scan(current.id)
    })
  }

  async function save() {
    if (!inspection) return
    const payload = Object.fromEntries(Object.entries(form).filter(([_, value]) => Boolean(value)))
    if (Object.keys(payload).length) {
      const { data } = await api.patch(`/inspections/${inspection.id}`, payload)
      setInspection(data)
    }
  }

  return <main className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
    <fieldset disabled={Boolean(busy)} className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif text-white font-bold">New Packaged Commodity Inspection</h1>
          <p className="text-xs text-slate-400 mt-1">{inspection ? `${inspection.inspection_code} · Draft saved` : 'Capture package photos to extract mandatory LMPC declarations.'}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-3 py-1 rounded font-bold ${step === 1 ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'}`}>1. Capture photos</span>
          <span className={`text-xs px-3 py-1 rounded font-bold ${step === 2 ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'}`}>2. Review & submit</span>
        </div>
      </div>

      {busy && <div className="p-4 bg-emerald-950/80 border border-emerald-800 rounded-xl text-xs text-emerald-300 flex items-center gap-3">
        <div className="w-4 h-4 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin shrink-0"></div>
        <span>{busy} {uploadProgress > 0 ? `(${uploadProgress}%)` : ''}</span>
      </div>}

      {error && <div className="p-4 bg-rose-950/80 border border-rose-800 rounded-xl text-xs text-rose-300">{error}</div>}
      {notice && <div className="p-4 bg-amber-950/80 border border-amber-800 rounded-xl text-xs text-amber-300">{notice}</div>}

      {cameraOpen && <WebcamModal onClose={() => setCameraOpen(false)} onCapture={(blob, panel) => {
        const file = new File([blob], `webcam_${panel}_${Date.now()}.jpg`, { type: 'image/jpeg' })
        selectFiles([file], panel)
        setCameraOpen(false)
      }} />}

      <input type="file" ref={uploadInput} multiple accept="image/*" className="hidden" onChange={e => selectFiles(e.target.files)} />
      <input type="file" ref={cameraInput} capture="environment" accept="image/*" className="hidden" onChange={e => selectFiles(e.target.files)} />

      {step === 1 ? <section className="glass-panel border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6">
        <div className="text-center max-w-lg mx-auto">
          <h2 className="text-xl font-serif font-bold text-white">Start with Package Evidence Photos</h2>
          <p className="text-xs text-slate-300 mt-2">Photograph the commodity packaging or upload label images. RapidOCR will scan all text and extract mandatory Rule 6 declarations.</p>
        </div>

        <div className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors ${dragging ? 'border-emerald-500 bg-emerald-950/30' : 'border-slate-700 bg-slate-900/60'}`}
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); selectFiles(e.dataTransfer.files) }}>
          <div className="text-4xl mb-2">📸</div>
          <p className="text-sm font-semibold text-slate-100">Drag & drop package photos here</p>
          <p className="text-xs text-slate-400 mt-1">Supports JPEG, PNG, WEBP up to 20MB per photo</p>
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            <button type="button" className={button} onClick={() => uploadInput.current?.click()}>Browse files</button>
            <button type="button" className={secondary} onClick={() => setCameraOpen(true)}>📷 Open Webcam Scanner</button>
          </div>
        </div>

        {images.length > 0 && <>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider border-b border-slate-800 pb-2">Uploaded Package Evidence ({images.length})</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">{images.map((img, index) => <article key={img.id} className="border border-slate-800 rounded-xl p-3 bg-slate-900/80">
            <AuthorizedImage src={img.content_url} alt={`Package photo ${index + 1}: ${img.original_filename}`} className="w-full aspect-square object-contain bg-slate-950 rounded-lg" />
            <p className="text-xs truncate mt-2 font-mono text-slate-300" title={img.original_filename}>{img.original_filename}</p>
            <label className="block text-xs mt-3 font-semibold text-slate-300">Package Panel Side
              <select className="w-full mt-1 border border-slate-700 rounded-lg p-2 bg-slate-950 text-slate-200 text-xs" value={img.panel_type} onChange={e => {
                const targetPanel = e.target.value
                operation('Updating panel side…', async () => {
                  await api.patch(`/inspections/${inspection.id}/images/${img.id}`, { panel_type: targetPanel })
                  await refresh(inspection.id)
                })
              }}>
                {PANELS.map(panel => <option key={panel} value={panel}>{panel.replaceAll('_', ' ')}</option>)}
              </select>
            </label>
            <button type="button" className="w-auto bg-transparent text-rose-400 hover:text-rose-300 text-xs underline mt-2 p-1 font-semibold" onClick={() => {
              operation('Removing photo…', async () => {
                await api.delete(`/inspections/${inspection.id}/images/${img.id}`)
                await refresh(inspection.id)
              })
            }}>Remove photo {index + 1}</button>
          </article>)}</div>
          <div className="flex justify-end mt-6"><button type="button" className={button} onClick={() => operation('Starting scan…', () => scan(inspection.id))}>{scanned ? 'Scan again' : 'Scan photos & extract'}</button></div>
        </>}
      </section> : <section className="glass-panel border border-slate-800 rounded-2xl p-5 sm:p-8">
        <h2 className="text-xl font-serif font-bold text-white">Mandatory LMPC Statutory Declarations & Review</h2>
        <div className="flex flex-wrap items-center justify-between gap-3 mt-2 mb-6">
          <p className="text-xs text-slate-300">Automated extraction for Legal Metrology (Packaged Commodities) Rules, 2011–2026.</p>
          <button type="button" className={secondary} onClick={() => operation('Scanning package text…', () => scan(inspection.id))}>{scanned ? 'Scan photos again' : 'Scan photos & extract'}</button>
        </div>

        {/* Mandatory 12 Declarations Status Grid */}
        <div className="mb-6 border border-slate-800 rounded-xl p-4 bg-slate-900/80">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 border-b border-slate-800 pb-2">
            LMPC Rule 6 Mandatory Statutory Declarations Status ({candidates.length} Detected)
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {MANDATORY_DECLARATIONS.map(item => {
              const matched = candidates.filter(c => c.declaration_type.toUpperCase().includes(item.type) || item.type.includes(c.declaration_type.toUpperCase()))
              const isFound = matched.length > 0
              const mainMatch = matched[0]

              return (
                <div key={item.type} className={`p-3 rounded-xl border text-xs flex flex-col justify-between ${isFound ? 'bg-slate-950 border-emerald-500/40 text-slate-100 shadow-sm' : 'bg-slate-950/60 border-slate-800 text-slate-400'}`}>
                  <div>
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span className="font-semibold text-slate-200">{item.label}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isFound ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400'}`}>
                        {isFound ? '✓ Extracted' : '○ Not Detected'}
                      </span>
                    </div>
                    {isFound && mainMatch && (
                      <p className="font-medium text-emerald-300 mt-1 line-clamp-2">{mainMatch.normalized_value}</p>
                    )}
                  </div>
                  {isFound && mainMatch && (
                    <div className="text-[10px] text-slate-400 mt-2 pt-1 border-t border-slate-800/80 flex justify-between font-mono">
                      <span>Confidence: {(mainMatch.confidence_score * 100).toFixed(0)}%</span>
                      <span className="font-mono text-emerald-400">{images.find(img => img.id === mainMatch.source_image_id)?.panel_type || 'PANEL'}</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {candidates.length > 0 && <details className="mt-6 border border-slate-800 rounded-xl p-4 bg-slate-900/90 text-slate-200" open>
          <summary className="cursor-pointer font-medium text-sm text-white">Extracted Statutory Candidates ({candidates.length})</summary>
          <div className="mt-3 divide-y divide-slate-800">{candidates.map(candidate => <div key={candidate.id} className="py-3 text-sm">
            <div className="flex flex-wrap justify-between gap-2"><span className="font-semibold text-emerald-400">{candidate.declaration_type.replaceAll('_', ' ')}</span><span className="font-mono text-xs text-slate-400">{Math.round(candidate.confidence_score * 100)}% confidence</span></div>
            <p className="font-medium whitespace-pre-wrap break-words mt-1 text-slate-100">{candidate.normalized_value}</p>
            {candidate.needs_review && <p className="text-xs text-amber-300 mt-1 bg-amber-950/60 p-2 rounded-lg border border-amber-800">Check against photo: {candidate.review_reasons.join('; ') || 'Review needed'}</p>}
            <p className="text-xs text-slate-400 mt-1 font-mono">{images.find(img => img.id === candidate.source_image_id)?.original_filename}</p>
          </div>)}</div>
        </details>}

        <div className="my-6">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">Package Evidence Photos ({images.length})</h3>
          <div className="flex gap-3 overflow-x-auto p-2 bg-slate-900/80 rounded-xl border border-slate-800">{images.map(img => <div key={img.id} className="shrink-0 border border-slate-800 rounded-lg p-1.5 bg-slate-950">
            <AuthorizedImage src={img.content_url} alt={img.original_filename} className="w-36 h-36 object-contain rounded-md" />
            <div className="text-[10px] font-semibold text-center mt-1 text-slate-400 uppercase">{img.panel_type}</div>
          </div>)}</div>
        </div>

        <div className="p-3.5 bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs rounded-xl mb-4 flex items-center justify-between shadow-sm">
          <span>⚡ <strong>Step 2 of 14 (Create & Submit Inspection):</strong> Click <strong className="underline">Submit inspection</strong> below to proceed to OCR, RuleLens Visualizer, Legal Rule Evaluation, and PDF Report.</span>
        </div>
        <p className="text-xs text-slate-400 mb-5">Submitting locks the inspection details and evidence photos. Check them before continuing.</p>
        <div className="flex flex-wrap justify-between gap-3 border-t border-slate-800 pt-5">
          <button type="button" className={secondary} onClick={() => operation('Saving details…', async () => { await save(); setStep(1) })}>Add or retake photos</button>
          <div className="flex flex-wrap gap-3">
            <button type="button" className={secondary} onClick={() => operation('Saving draft…', async () => { await save(); navigate('/inspections') })}>Save draft & exit</button>
            <button type="button" className={button} disabled={!images.length} onClick={() => operation('Submitting & analyzing…', async () => {
              await save()
              setBusy('Submitting inspection…')
              const { data } = await api.post(`/inspections/${inspection.id}/submit`)
              setBusy('Running automated Legal Metrology compliance analysis (OCR, Rule 6 Parser, Rule Engine, PDF Generator)…')
              let verdictMsg = 'submitted'
              try {
                const { data: result } = await api.post(`/inspections/${data.id}/analysis`, null, { timeout: 600000 })
                verdictMsg = `analyzed with final verdict: ${result.final_compliance_status}`
              } catch (e) {
                console.warn('Auto-analysis warning:', e)
              }
              navigate(`/inspections/${data.id}`, { state: { message: `Inspection ${data.inspection_code} ${verdictMsg}. Compliance report & PDF export ready below.` } })
            })}>Submit & Run Full Automated Analysis</button>
          </div>
        </div>
      </section>}
    </fieldset>
  </main>
}
