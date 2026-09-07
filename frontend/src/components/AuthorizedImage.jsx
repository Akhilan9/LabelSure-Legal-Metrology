import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function AuthorizedImage({ src, alt, className, onClick, onLoad }) {
  const [blobUrl, setBlobUrl] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let isMounted = true
    let activeUrl = null

    if (!src) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(false)

    let cleanSrc = src
    if (cleanSrc.startsWith('http://') || cleanSrc.startsWith('https://')) {
      try {
        cleanSrc = new URL(cleanSrc).pathname
      } catch (e) {}
    }
    if (cleanSrc.startsWith('/api/v1/')) {
      cleanSrc = cleanSrc.slice(8)
    } else if (cleanSrc.startsWith('/api/v1')) {
      cleanSrc = cleanSrc.slice(7)
    }
    if (cleanSrc.startsWith('/')) {
      cleanSrc = cleanSrc.slice(1)
    }

    api.get(cleanSrc, { responseType: 'blob' })
      .then(response => {
        if (!isMounted) return
        activeUrl = URL.createObjectURL(response.data)
        setBlobUrl(activeUrl)
        setLoading(false)
      })
      .catch(() => {
        if (!isMounted) return
        setError(true)
        setLoading(false)
      })

    return () => {
      isMounted = false
      if (activeUrl) {
        URL.revokeObjectURL(activeUrl)
      }
    }
  }, [src])

  if (loading) {
    return (
      <div className={`flex items-center justify-center bg-stone-100 text-stone-400 text-xs ${className}`}>
        <span>Loading…</span>
      </div>
    )
  }

  if (error || !blobUrl) {
    return (
      <div className={`flex items-center justify-center bg-stone-100 text-stone-400 text-xs ${className}`}>
        <span>No Preview</span>
      </div>
    )
  }

  return (
    <img
      src={blobUrl}
      alt={alt || 'Inspection Evidence'}
      className={className}
      onClick={onClick}
      onLoad={onLoad}
    />
  )
}
