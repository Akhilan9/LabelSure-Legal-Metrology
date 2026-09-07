import { useEffect, useState } from 'react'
import { api } from '../api/client'
import OCRBoundingBoxCanvas from './OCRBoundingBoxCanvas'

export default function ExtractedDeclarations({ inspection, user, refreshKey, onExtractionComplete }) {
  const [candidates, setCandidates] = useState([])
  const [summary, setSummary] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [selectedBlock, setSelectedBlock] = useState(null)
  const base = '/inspections/' + inspection.id
  const canRun = user?.role === 'INSPECTOR' || (user?.role === 'INSPECTOR' && user.id === inspection.created_by_user_id)

  async function load(signal) {
    const [list, report] = await Promise.all([
      api.get(base + '/declarations?limit=1000', { signal }),
      api.get(base + '/extraction-summary', { signal }),
    ])
    if (!signal?.aborted) {
      setCandidates(list.data); setSummary(report.data); setSelected(null)
    }
  }
  useEffect(() => {
    const controller = new AbortController()
    setError('')
    load(controller.signal).catch(e => { if (!controller.signal.aborted) setError(e.response?.data?.detail || 'Unable to load declarations.') })
    return () => controller.abort()
  }, [inspection.id, refreshKey])

  async function run() {
    setBusy(true); setError('')
    try {
      await api.post(base + '/extract-declarations', null, { timeout: 30000 })
      await load()
      onExtractionComplete?.()
    } catch (e) {
      setError(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Unable to extract declarations.')
    } finally { setBusy(false) }
  }

  return <section className="panel my-6">
    <div className="flex justify-between gap-4 items-center">
      <h2>Extracted Declarations</h2>
      {canRun && <button onClick={run} disabled={busy}>{busy ? 'Extracting…' : 'Extract declarations'}</button>}
    </div>
    <p className="text-sm text-stone-600 my-3">Machine-generated candidates for inspector review. Extraction does not establish legal compliance. A missing candidate does not prove a declaration is absent.</p>
    {error && <p role="alert" className="text-rose-800 my-3">{error}</p>}
    {summary?.run && <p className="text-xs text-stone-600 mb-3">
      {summary.candidate_count} candidates · {summary.needs_review_count} need review · Extraction version {summary.run.version}
    </p>}
    {summary?.run?.warnings?.map(w => <p key={w} className="text-amber-800 text-sm">{w}</p>)}
    {summary?.conflicting_types?.length > 0 && <div role="status" className="bg-amber-50 border border-amber-300 p-3 my-3">
      Review required: conflicting candidates for {summary.conflicting_types.map(t => t.replaceAll('_', ' ')).join(', ')}. No primary candidate has been chosen for these types.
    </div>}
    {!candidates.length && <p className="text-stone-500 my-4">{summary?.run ? 'No supported declarations were detected in the current OCR evidence.' : 'Run OCR, then extract declarations. Updated OCR evidence requires a new extraction.'}</p>}
    <div className="overflow-x-auto">
      {candidates.length > 0 && <table className="w-full text-left text-sm">
        <thead><tr>{['Declaration', 'Value', 'Confidence', 'Panel / Image', 'Method', 'Review', 'Evidence'].map(h => <th key={h} className="p-2 border-b">{h}</th>)}</tr></thead>
        <tbody>{candidates.map(c => <tr key={c.id} className={c.needs_review ? 'bg-amber-50' : ''}>
          <td className="p-2">{c.declaration_type.replaceAll('_', ' ')}{c.is_primary && <small className="block text-stone-500">Primary candidate</small>}</td>
          <td className="p-2 whitespace-pre-wrap break-words">{c.declaration_type === 'MRP' ? '₹' : ''}{c.normalized_value}</td>
          <td className="p-2">{Math.round(c.confidence_score * 100)}%</td>
          <td className="p-2">{c.panel_type}<small className="block">{inspection.images?.find(i => i.id === c.source_image_id)?.original_filename || c.source_image_id}</small></td>
          <td className="p-2">{c.extraction_method.replaceAll('_', ' ')}</td>
          <td className="p-2">{c.needs_review ? 'Review required' : 'Auto extracted'}<small className="block">{c.review_reasons.join('; ')}</small></td>
          <td className="p-2"><button onClick={() => { setSelected(c); setSelectedBlock(c.sources[0]?.ocr_block_id) }}>View evidence</button></td>
        </tr>)}</tbody>
      </table>}
    </div>
    {selected && <div className="mt-5 border border-stone-300 rounded p-4">
      <div className="flex justify-between"><h3>Source evidence · {selected.declaration_type.replaceAll('_', ' ')}</h3><button onClick={() => setSelected(null)}>Close evidence</button></div>
      <p className="text-xs text-stone-500 my-2">OCR run: {selected.source_ocr_run_id}</p>
      <OCRBoundingBoxCanvas
        key={selected.id}
        imageUrl={base + '/images/' + selected.source_image_id + (selected.source_image_variant === 'processed' ? '/processed' : '/content')}
        altText="Declaration source evidence"
        blocks={selected.sources.map(s => ({ ...s, id: s.ocr_block_id, confidence_tier: 'REVIEW', reading_order: s.sequence_order }))}
        selectedBlockId={selectedBlock}
        onSelectBlock={b => setSelectedBlock(typeof b === 'string' ? b : b.id)}
        onHoverBlock={() => {}}
      />
      <h4 className="mt-3 font-semibold">Raw OCR text</h4>
      {selected.sources.map(s => <button className="block text-left whitespace-pre-wrap break-words my-2" key={s.ocr_block_id} onClick={() => setSelectedBlock(s.ocr_block_id)}>{s.sequence_order + 1}. {s.raw_text}</button>)}
      <p className="text-xs text-stone-600">Confidence contributions: {Object.entries(selected.confidence_factors).map(([k, v]) => k + ' ' + Math.round(v * 100) + '%').join(' · ')}</p>
    </div>}
  </section>
}

