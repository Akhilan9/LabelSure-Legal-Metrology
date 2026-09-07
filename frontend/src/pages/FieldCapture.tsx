import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Camera, CloudUpload, Wifi, WifiOff } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { listLocal, saveLocal, removeLocal, type OfflineCase } from '../api/offline'
import { validatePhotos } from '../api/scan'
import WebcamModal from '../components/WebcamModal'
export default function FieldCapture() {
 const {user}=useAuth()
 const [items,setItems]=useState<OfflineCase[]>([]),[camera,setCamera]=useState(false),[online,setOnline]=useState(navigator.onLine),[paused,setPaused]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const syncing=useRef(false)
 const active=useRef(true)
 async function refresh(){setItems(await listLocal(user.id))}
 useEffect(()=>{active.current=true;refresh().catch(()=>setError('Local storage is unavailable.'));const update=()=>setOnline(navigator.onLine);window.addEventListener('online',update);window.addEventListener('offline',update);return()=>{active.current=false;window.removeEventListener('online',update);window.removeEventListener('offline',update)}},[user.id])
 async function capture(files:File[],panel='FRONT') {try{validatePhotos(files);await saveLocal({id:crypto.randomUUID(),owner:user.id,name:files[0]?.name||'Field capture',photos:files.map(file=>({file,panel})),state:'DRAFT',updated:Date.now(),uploaded:0});await refresh()}catch(e){setError(e instanceof Error?e.message:'Could not save photos locally.')}}
 async function sync(){if(syncing.current||!online||paused)return;syncing.current=true;setBusy(true);setError('');try{
  for(const item of await listLocal(user.id)){
   if(!active.current||!navigator.onLine)break
   if(!['QUEUED','UPLOADING','ANALYZING'].includes(item.state))continue
   try{
    item.state='UPLOADING';await saveLocal(item);await refresh()
    const {data:inspection}=await api.post('/inspections',{client_id:item.id})
    // Compare original file hashes with server evidence before retrying an interrupted upload.
    const {data:existing}=await api.get(`/inspections/${inspection.id}/images`)
    const hashes=new Set(existing.map((image:{sha256:string})=>image.sha256))
    for(let i=0;i<item.photos.length;i++){
     if(!active.current)break
     const photo=item.photos[i]
     const digest=await crypto.subtle.digest('SHA-256',await photo.file.arrayBuffer())
     const hash=Array.from(new Uint8Array(digest)).map(value=>value.toString(16).padStart(2,'0')).join('')
     if(!hashes.has(hash)){const body=new FormData();body.append('files',photo.file,photo.file.name);body.append('panel_types',photo.panel);await api.post(`/inspections/${inspection.id}/images`,body,{timeout:120000});hashes.add(hash)}
     item.uploaded=i+1;await saveLocal(item)
    }
    if(!active.current)break
    item.state='ANALYZING';await saveLocal(item);await refresh()
    await api.post(`/inspections/${inspection.id}/analysis`,null,{timeout:600000})
    item.state='REVIEW_REQUIRED';item.error=undefined
   }catch(e:any){item.state=navigator.onLine?'ERROR':'QUEUED';item.error=typeof e.response?.data?.detail==='string'?e.response.data.detail:'Sync interrupted. Saved photos remain on this device.'}
   await saveLocal(item);if(active.current)await refresh()
  }
 }finally{syncing.current=false;if(active.current)setBusy(false)}}
 useEffect(()=>{if(online&&!paused&&items.some(item=>['QUEUED','UPLOADING','ANALYZING'].includes(item.state)))sync()},[online,paused,items])
 async function queue(item:OfflineCase){item.state='QUEUED';item.error=undefined;await saveLocal(item);await refresh()}
 return <main className="max-w-5xl mx-auto p-6"><div className="eyebrow">FIELD WORKSPACE</div><h1 className="text-3xl font-serif my-3">Offline capture</h1><p>Keep package photos on this device, then sync them when connected.</p>
 <div className="flex flex-wrap gap-3 my-5 items-center"><span className="flex items-center gap-2">{online?<Wifi size={18}/>:<WifiOff size={18}/>} {online?'Connected':'Offline'}</span><label className="flex items-center gap-2"><input type="checkbox" checked={paused} onChange={e=>setPaused(e.target.checked)}/>Pause automatic sync</label><button type="button" className="w-auto flex gap-2 items-center" onClick={()=>setCamera(true)}><Camera size={18}/>Open camera</button><label className="border rounded px-4 py-2 cursor-pointer">Save photos<input type="file" className="hidden" multiple accept="image/jpeg,image/png,image/webp" onChange={e=>{capture(Array.from(e.target.files||[]));e.target.value=''}}/></label></div>
 {camera&&<WebcamModal onClose={()=>setCamera(false)} onCapture={(file:File,panel:string)=>capture([file],panel)}/>}{error&&<p role="alert">{error}</p>}
 <div className="space-y-4">{items.map(item=><article className="panel" key={item.id}><div className="flex flex-wrap justify-between gap-3"><div><h2>{item.name}</h2><p>{item.photos.length} photos · {item.state.replaceAll('_',' ')}</p><small>{item.uploaded} uploaded</small></div><div className="flex gap-3 items-center">{['DRAFT','ERROR'].includes(item.state)&&<button className="w-auto flex gap-2" disabled={busy} onClick={()=>queue(item)}><CloudUpload size={18}/>{item.state==='ERROR'?'Retry sync':'Queue for sync'}</button>}{item.uploaded>0&&<Link className="underline" to={`/inspections/new?draft=${item.id}`}>Review saved case</Link>}<button disabled={busy} className="w-auto" onClick={async()=>{if(window.confirm('Remove this local copy? Photos already uploaded remain on the server.')){await removeLocal(item.id);await refresh()}}}>Remove local copy</button></div></div>{item.error&&<p className="mt-3 text-amber-800" role="status">{item.error}</p>}</article>)}</div>{!items.length&&<p className="my-8 text-stone-500">No photos stored on this device yet.</p>}</main>
}
