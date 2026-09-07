import { useEffect, useRef, useState } from 'react'

export default function WebcamModal({ onCapture, onClose }) {
  const video = useRef(null)
  const stream = useRef(null)
  const dialog = useRef(null)
  const [devices, setDevices] = useState([])
  const [device, setDevice] = useState('')
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [panel, setPanel] = useState('FRONT')
  const [capturing, setCapturing] = useState(false)
  useEffect(() => {
    dialog.current.showModal()
    return () => stream.current?.getTracks().forEach(track => track.stop())
  }, [])
  useEffect(() => {
    let cancelled = false
    setReady(false); setError('')
    stream.current?.getTracks().forEach(track => track.stop())
    async function start() {
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error('Live camera requires HTTPS or localhost. You can still upload a saved photo.')
        const current = await navigator.mediaDevices.getUserMedia({ audio: false, video: {
          ...(device ? { deviceId: { exact: device } } : { facingMode: { ideal: 'environment' } }),
          width: { ideal: 1920 }, height: { ideal: 1080 },
        } })
        if (cancelled) { current.getTracks().forEach(track => track.stop()); return }
        stream.current = current
        video.current.srcObject = current
        await video.current.play()
        const available = await navigator.mediaDevices.enumerateDevices()
        if (!cancelled) setDevices(available.filter(item => item.kind === 'videoinput'))
      } catch (e) {
        if (!cancelled) setError(e.name === 'NotAllowedError' ? 'Camera permission was denied. Allow camera access in your browser, or upload a saved photo.' : e.name === 'NotFoundError' ? 'No camera found. Connect a camera or upload a saved photo.' : e.message)
      }
    }
    start()
    return () => { cancelled = true; stream.current?.getTracks().forEach(track => track.stop()) }
  }, [device])
  async function capture() {
    if (!ready || capturing) return
    setCapturing(true)
    try {
      const canvas = document.createElement('canvas')
      canvas.width = video.current.videoWidth; canvas.height = video.current.videoHeight
      canvas.getContext('2d').drawImage(video.current, 0, 0)
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.95))
      if (!blob) throw new Error('Could not capture this frame. Please try again.')
      onCapture(new File([blob], `package-${Date.now()}.jpg`, { type: 'image/jpeg' }), panel)
      onClose()
    } catch (e) { setError(e.message); setCapturing(false) }
  }
  return <dialog ref={dialog} onCancel={onClose} aria-labelledby="camera-title" className="m-auto w-[min(95vw,900px)] rounded-xl p-5 bg-stone-950 text-white backdrop:bg-black/80">
    <div className="flex justify-between items-center mb-4"><h2 id="camera-title" className="text-xl">Live package scanner</h2><button type="button" className="w-auto px-3" onClick={onClose} aria-label="Close camera">Close</button></div>
    {error && <p role="alert" className="p-3 bg-red-950 text-red-100 mb-3">{error}</p>}
    <div className="relative bg-black rounded overflow-hidden">
      <video ref={video} autoPlay muted playsInline onLoadedData={() => setReady(true)} className="w-full max-h-[60vh]" />
      <div aria-hidden="true" className="absolute inset-[12%] border-2 border-emerald-400 rounded-lg pointer-events-none" />
    </div>
    <p className="text-sm my-3">Align the label inside the guide. Avoid glare and hold steady.</p>
    <div className="flex flex-wrap gap-3 items-end">
      <label className="flex-1 text-sm">Camera<select className="block w-full p-2 mt-1 bg-stone-800" value={device} onChange={e => setDevice(e.target.value)}><option value="">Automatic rear camera</option>{devices.map((item, i) => <option value={item.deviceId} key={item.deviceId}>{item.label || `Camera ${i + 1}`}</option>)}</select></label>
      <label className="text-sm">Panel<select className="block p-2 mt-1 bg-stone-800" value={panel} onChange={e => setPanel(e.target.value)}>{['FRONT', 'BACK', 'LEFT', 'RIGHT', 'MRP_PANEL', 'DECLARATION_PANEL'].map(value => <option key={value}>{value}</option>)}</select></label>
      <button type="button" disabled={!ready || capturing} onClick={capture} className="w-auto rounded bg-emerald-700 px-5 py-3 disabled:opacity-50">{capturing ? 'Capturing…' : 'Capture photo'}</button>
    </div>
  </dialog>
}
