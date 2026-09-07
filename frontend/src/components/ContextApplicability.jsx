import { useEffect, useState } from 'react'
import { api } from '../api/client'

const fields = [
  ['package_type', 'Package type', ['PACKET','BOX','BOTTLE','JAR','CAN','POUCH','TUBE','CARTON','OTHER','UNKNOWN']],
  ['product_category', 'Product category', ['FOOD','COSMETIC','HOUSEHOLD','PERSONAL_CARE','ELECTRONICS','OTHER','UNKNOWN']],
  ['import_status', 'Import status', ['DOMESTIC','IMPORTED','UNKNOWN']],
  ['quantity_kind', 'Quantity kind', ['WEIGHT','VOLUME','COUNT','LENGTH','AREA','UNKNOWN']],
]
const label = value => String(value ?? 'Unknown').replaceAll('_', ' ')
const display = value => value === null ? 'Unknown' : value === false ? 'No candidate detected' : value === true ? 'Yes' : label(value)

export default function ContextApplicability({ inspection, user, refreshKey, ocrRefresh }) {
  const [context, setContext] = useState(null)
  const [facts, setFacts] = useState([])
  const [preview, setPreview] = useState([])
  const [input, setInput] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [debug, setDebug] = useState(null)
  const base = '/inspections/' + inspection.id
  const canResolve = user?.role === 'INSPECTOR' || (user?.role === 'INSPECTOR' && user.id === inspection.created_by_user_id)

  async function load(signal) {
    const response = await api.get(base + '/context', { signal })
    if (signal?.aborted) return
    setContext(response.data); setDebug(null)
    if (response.data.run) {
      const [f, p] = await Promise.all([api.get(base + '/context/facts', { signal }), api.get(base + '/applicability-preview', { signal })])
      if (!signal?.aborted) { setFacts(f.data); setPreview(p.data.items) }
    } else { setFacts([]); setPreview([]) }
  }
  useEffect(() => {
    const controller = new AbortController()
    setError('')
    load(controller.signal).catch(e => { if (!controller.signal.aborted) setError(e.response?.data?.detail || 'Unable to load context.') })
    return () => controller.abort()
  }, [inspection.id, inspection.updated_at, refreshKey, ocrRefresh])

  async function resolve(clear = false) {
    setBusy(true); setError('')
    const values = clear ? Object.fromEntries([...fields.map(f => f[0]), 'country_of_origin'].map(k => [k, null])) :
      Object.fromEntries(Object.entries(input).filter(([, v]) => v !== ''))
    try {
      await api.post(base + '/resolve-context', { inspector_input: values }, { timeout: 30000 })
      setInput({})
      await load()
    } catch (e) {
      setError(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Unable to resolve context. Check the entered values.')
    } finally { setBusy(false) }
  }
  async function showDebug() {
    try { setDebug((await api.get(base + '/rule-input')).data) }
    catch { setError('Unable to load the current rule-input snapshot.') }
  }

  return <section className="panel my-6">
    <h2>Context &amp; Applicability</h2>
    <p className="text-sm text-stone-600 my-3">Context and candidate detection prepare an inspection for later evaluation. This preview does not determine legal compliance.</p>
    {error && <p role="alert" className="text-rose-800">{typeof error === 'string' ? error : 'Unable to load context.'}</p>}
    {canResolve && <details className="my-4 border border-stone-200 p-3 rounded">
      <summary className="cursor-pointer font-semibold">Inspector context input</summary>
      <p className="text-xs text-stone-500 my-2">Optional inputs are saved separately from inspection metadata. Competing evidence remains visible.</p>
      <div className="grid md:grid-cols-2 gap-3">
        {fields.map(([key, name, options]) => <label key={key} className="text-sm">{name}
          <select value={input[key] || ''} onChange={e => setInput({ ...input, [key]: e.target.value })} className="block w-full border p-2 rounded">
            <option value="">Keep saved input / metadata</option>
            {options.map(v => <option key={v} value={v}>{label(v)}</option>)}
          </select>
        </label>)}
        <label className="text-sm">Country of origin
          <input maxLength={100} value={input.country_of_origin || ''} onChange={e => setInput({ ...input, country_of_origin: e.target.value })} className="block w-full border p-2 rounded" />
        </label>
      </div>
      {context?.inspector_input && <p className="text-xs text-stone-600 mt-3">Saved inputs: {Object.entries(context.inspector_input).map(([k,v]) => label(k) + ': ' + label(v)).join(' · ') || 'None'}</p>}
      <button className="mt-3" disabled={busy} onClick={() => resolve(true)}>Clear saved inputs and resolve</button>
    </details>}
    {canResolve && <button disabled={busy} onClick={() => resolve()}>{busy ? 'Resolving…' : 'Resolve context'}</button>}
    {!context?.run && <p className="text-stone-500 my-3">No current context snapshot. Resolve context after evidence, extraction, or metadata changes. Resolution can begin before OCR; limitations will be shown.</p>}
    {context?.run && <>
      <h3 className="font-semibold mt-5 mb-3">Product and package context</h3>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {['PRODUCT_CATEGORY','PACKAGE_TYPE','IMPORT_STATUS','COUNTRY_OF_ORIGIN','QUANTITY_KIND'].map(key => {
          const fact = context.resolved[key]
          return <article key={key} className={'p-3 border rounded ' + (['CONFLICTING','REVIEW_REQUIRED'].includes(fact.state) ? 'bg-amber-50 border-amber-300' : 'border-stone-200')}>
            <h4 className="text-xs text-stone-500">{label(key)}</h4>
            <p className="font-semibold">{display(fact.value)}</p>
            <p className="text-xs">{label(fact.state)} · {label(fact.source_type)}</p>
            {fact.confidence !== null && <p className="text-xs">Source confidence: {Math.round(fact.confidence * 100)}%</p>}
          </article>
        })}
      </div>
      <h3 className="font-semibold mt-5">Evidence sufficiency</h3>
      <p className="my-2">{label(context.evidence.state)}</p>
      {context.evidence.reasons.map(r => <p key={r} className="text-sm text-stone-600">{r}</p>)}
      {context.conflicts.length > 0 && <div role="status" className="my-4 p-3 bg-amber-50 border border-amber-300 rounded">
        <h3 className="font-semibold">Conflicts / review required</h3>
        {context.conflicts.map(c => <div key={c.fact_type} className="mt-3">
          <strong>{label(c.fact_type)}</strong>
          {c.sources.map(s => <p key={s.fact_id} className="text-sm whitespace-pre-wrap">{label(s.source_type)}: {display(s.value)} — {s.raw}</p>)}
          <p className="text-xs">{c.reason}</p>
        </div>)}
      </div>}
      <details className="my-4">
        <summary className="cursor-pointer font-semibold">Context facts and sources ({facts.length})</summary>
        <div className="overflow-x-auto"><table className="w-full text-left text-xs mt-3">
          <thead><tr>{['Fact','Value','State','Source','Evidence / explanation'].map(h => <th key={h} className="p-2 border-b">{h}</th>)}</tr></thead>
          <tbody>{facts.map(f => <tr key={f.id}>
            <td className="p-2">{label(f.fact_type)}</td>
            <td className="p-2">{display(f.value.normalized)}</td>
            <td className="p-2">{label(f.resolution_state)}</td>
            <td className="p-2">{label(f.source_type)}<small className="block break-all">{f.source_reference_id}</small></td>
            <td className="p-2 whitespace-pre-wrap break-words">{String(f.value.raw ?? 'Unknown')}<small className="block">{f.explanation}</small></td>
          </tr>)}</tbody>
        </table></div>
      </details>
      <h3 className="font-semibold mt-4">Applicability preview</h3>
      <p className="text-sm text-amber-800 my-2">Legal verification pending. These preparation hints cannot execute rules.</p>
      <div className="grid md:grid-cols-2 gap-3">{preview.map(p => <article key={p.rule_key} className="border border-stone-200 rounded p-3">
        <h4 className="font-medium text-sm">{label(p.rule_key.replace('DECLARATION_', ''))} declaration</h4>
        <p className="text-sm">{label(p.state)}</p><p className="text-xs text-stone-500">{p.reason}</p>
      </article>)}</div>
      {user?.role === 'INSPECTOR' && <details className="mt-4"><summary onClick={() => { if (!debug) showDebug() }} className="cursor-pointer">Rule input snapshot (admin)</summary>
        {debug && <pre className="text-xs overflow-auto max-h-96 whitespace-pre-wrap break-words">{JSON.stringify(debug, null, 2)}</pre>}
      </details>}
    </>}
  </section>
}

