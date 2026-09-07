import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'EVIDENCE_UPLOADED', label: 'Evidence Uploaded' },
  { value: 'READY_FOR_ANALYSIS', label: 'Ready for Analysis' },
]

export default function InspectionsList() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [inspections, setInspections] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchInspections = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: pageSize }
      if (statusFilter) params.status = statusFilter
      if (searchQuery.trim()) params.q = searchQuery.trim()

      const { data } = await api.get('/inspections', { params })
      setInspections(data.items || [])
      setTotal(data.total || 0)
    } catch (err) {
      setError('Failed to load inspections list.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchInspections()
  }, [page, statusFilter])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setPage(1)
    fetchInspections()
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'DRAFT':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-stone-100 text-stone-700 border border-stone-300">Draft</span>
      case 'EVIDENCE_UPLOADED':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-100 text-blue-800 border border-blue-200">Evidence Uploaded</span>
      case 'READY_FOR_ANALYSIS':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">Ready for Analysis</span>
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-stone-100 text-stone-800">{status}</span>
    }
  }

  const canCreate = user && ['INSPECTOR'].includes(user.role)

  const [selectedIds, setSelectedIds] = useState([])
  const [bulkProcessing, setBulkProcessing] = useState(false)

  const toggleSelectAll = () => {
    if (selectedIds.length === inspections.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(inspections.map(i => i.id))
    }
  }

  const toggleSelectOne = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const handleBulkScan = async () => {
    if (!selectedIds.length) return
    setBulkProcessing(true)
    setError(null)
    try {
      const { data } = await api.post('/inspections/bulk-analysis', { inspection_ids: selectedIds })
      alert(`Bulk scanning completed! Processed ${data.total} inspections.`)
      setSelectedIds([])
      fetchInspections()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to complete bulk scanning.')
    } finally {
      setBulkProcessing(false)
    }
  }

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-stone-300">
        <div>
          <div className="eyebrow">REGULATORY LOG & REPOSITORY</div>
          <h1 className="text-3xl font-serif text-stone-900 mt-1">Inspection Repository</h1>
          <p className="text-xs text-stone-600 mt-1">
            Browse, search, and verify packaged commodity inspections and submitted photographic evidence.
          </p>
        </div>
        {canCreate && (
          <Link
            to="/inspections/new"
            className="w-auto px-5 py-2.5 text-xs bg-emerald-900 hover:bg-emerald-800 text-white font-semibold rounded shadow flex items-center gap-1.5 self-start sm:self-auto"
          >
            <span>+ New Inspection</span>
          </Link>
        )}
      </div>

      {/* Bulk Action Bar */}
      {selectedIds.length > 0 && (
        <div className="my-4 p-4 bg-emerald-950 text-white rounded-xl border border-emerald-800 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
          <div className="text-xs font-semibold">
            <span>⚡ Bulk Action: <strong>{selectedIds.length}</strong> inspection{selectedIds.length > 1 ? 's' : ''} selected</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled={bulkProcessing}
              onClick={handleBulkScan}
              className="w-auto px-5 py-2 text-xs bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg shadow transition-all"
            >
              {bulkProcessing ? 'Scanning Packages…' : '⚡ Bulk Scan Selected Packages'}
            </button>
            <button
              type="button"
              onClick={() => setSelectedIds([])}
              className="w-auto px-3 py-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700"
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="my-6 bg-white p-4 border border-stone-300 rounded-lg shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex gap-2 w-full md:w-96">
          <input
            type="text"
            placeholder="Search code, product, brand, barcode…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs p-2.5 border border-stone-300 rounded bg-stone-50 focus:bg-white focus:outline-emerald-800"
          />
          <button
            type="submit"
            className="w-auto px-4 py-2 text-xs bg-stone-800 hover:bg-stone-900 text-white rounded font-medium"
          >
            Search
          </button>
        </form>

        {/* Status filter tabs */}
        <div className="flex items-center gap-1 overflow-x-auto w-full md:w-auto">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                setStatusFilter(opt.value)
                setPage(1)
              }}
              className={`w-auto px-3 py-1.5 text-xs rounded transition-colors whitespace-nowrap ${
                statusFilter === opt.value
                  ? 'bg-emerald-900 text-white font-semibold'
                  : 'bg-stone-100 hover:bg-stone-200 text-stone-700'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-700 text-red-800 text-xs rounded">
          {error}
        </div>
      )}

      {/* Table / List */}
      {loading ? (
        <div className="p-12 text-center text-xs text-stone-500 bg-white border border-stone-200 rounded">
          Loading inspections…
        </div>
      ) : inspections.length === 0 ? (
        <div className="p-12 text-center bg-white border border-stone-200 rounded-lg shadow-sm">
          <div className="text-3xl mb-2">📋</div>
          <h3 className="text-base font-serif text-stone-800 font-semibold mb-1">No inspections found</h3>
          <p className="text-xs text-stone-500 max-w-sm mx-auto mb-4">
            {searchQuery || statusFilter
              ? 'No inspections matched your filter query. Try clearing search or status filters.'
              : 'No package inspections have been recorded yet in your workspace.'}
          </p>
          {canCreate && !searchQuery && !statusFilter && (
            <Link
              to="/inspections/new"
              className="inline-block px-5 py-2 text-xs bg-emerald-900 hover:bg-emerald-800 text-white font-medium rounded"
            >
              Create First Inspection
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-white border border-stone-300 rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-stone-100 border-b border-stone-300 text-stone-600 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="p-3.5 pl-4 w-8">
                    <input
                      type="checkbox"
                      checked={inspections.length > 0 && selectedIds.length === inspections.length}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th className="p-3.5">Code</th>
                  <th className="p-3.5">Product & Brand</th>
                  <th className="p-3.5">Category</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Evidence</th>
                  <th className="p-3.5">Created By</th>
                  <th className="p-3.5">Date</th>
                  <th className="p-3.5 pr-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200">
                {inspections.map((insp) => (
                  <tr
                    key={insp.id}
                    onClick={() => navigate(`/inspections/${insp.id}`)}
                    className="hover:bg-stone-50 cursor-pointer transition-colors"
                  >
                    <td className="p-3.5 pl-4" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(insp.id)}
                        onChange={() => toggleSelectOne(insp.id)}
                      />
                    </td>
                    <td className="p-3.5 font-mono font-bold text-stone-900">
                      {insp.inspection_code}
                    </td>
                    <td className="p-3.5">
                      <div className="font-semibold text-stone-900">{insp.product_name || '—'}</div>
                      <div className="text-[11px] text-stone-500">{insp.brand_name || 'No brand specified'}</div>
                    </td>
                    <td className="p-3.5 text-stone-700">
                      {insp.category || '—'}
                    </td>
                    <td className="p-3.5">
                      {getStatusBadge(insp.status)}
                    </td>
                    <td className="p-3.5 text-stone-700">
                      <span className="font-medium">{insp.images_count}</span>{' '}
                      <span className="text-stone-400">image{insp.images_count !== 1 ? 's' : ''}</span>
                    </td>
                    <td className="p-3.5 text-stone-700">
                      {insp.created_by_name || 'Inspector'}
                    </td>
                    <td className="p-3.5 text-stone-500 whitespace-nowrap">
                      {new Date(insp.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="p-3.5 pr-4 text-right">
                      <Link
                        to={`/inspections/${insp.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-emerald-900 hover:text-emerald-700 font-semibold underline text-xs"
                      >
                        Details →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination bar */}
          <div className="p-4 border-t border-stone-200 bg-stone-50 flex items-center justify-between text-xs text-stone-600">
            <span>
              Showing {inspections.length} of {total} inspections
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="w-auto px-3 py-1 bg-white border border-stone-300 rounded disabled:opacity-40"
              >
                Previous
              </button>
              <span className="px-2 py-1 font-mono">Page {page}</span>
              <button
                type="button"
                disabled={page * pageSize >= total}
                onClick={() => setPage((p) => p + 1)}
                className="w-auto px-3 py-1 bg-white border border-stone-300 rounded disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
