import { useEffect, useState } from 'react'
import { api } from '../api/client'
type Rule = { rule_id: string; title: string; legal_reference: string; legal_status: string; verification_metadata: {source?: string}; required_declaration_types: string[] }
type RuleSet = {ruleset_id: string; description: string; rules: Rule[]}
export default function RulesRepository() {
  const [items,setItems]=useState<RuleSet[]>([])
  const [selected,setSelected]=useState('')
  const [query,setQuery]=useState('')
  const [error,setError]=useState('')
  useEffect(()=>{const controller=new AbortController();api.get('/rules',{signal:controller.signal}).then(({data})=>{setItems(data.items);setSelected(data.configured)}).catch(()=>{if(!controller.signal.aborted)setError('Could not load the rule repository.')});return()=>controller.abort()},[])
  const current=items.find(item=>item.ruleset_id===selected)
  return <main className="p-6 max-w-6xl mx-auto"><div className="eyebrow">LEGAL SOURCES</div><h1 className="text-3xl font-serif my-3">Versioned rule repository</h1>
    {error&&<p role="alert">{error}</p>}
    <div className="flex flex-wrap gap-4 my-5"><label>Review profile<select className="block border rounded p-2" value={selected} onChange={e=>setSelected(e.target.value)}>{items.map(item=><option key={item.ruleset_id}>{item.ruleset_id}</option>)}</select></label><label>Search rules<input className="block border rounded p-2" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Name or citation"/></label></div>
    <p className="text-sm text-amber-800 p-4 bg-amber-50 rounded mb-5">{current?.description}</p>
    <div className="grid md:grid-cols-2 gap-4">{current?.rules.filter(rule=>(rule.title+' '+rule.legal_reference).toLowerCase().includes(query.toLowerCase())).map(rule=><article key={rule.rule_id} className="panel"><h2>{rule.title}</h2><p className="text-sm my-2">{rule.legal_reference}</p><p className="text-xs mb-3">{rule.legal_status.replaceAll('_',' ')}</p><p className="text-xs text-stone-500 mb-3">Evidence: {rule.required_declaration_types.join(', ')}</p>{rule.verification_metadata.source&&<a className="text-emerald-800 underline" href={rule.verification_metadata.source} target="_blank" rel="noreferrer">Official source</a>}</article>)}</div>
  </main>
}
