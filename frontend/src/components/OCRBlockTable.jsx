import { useMemo, useState } from 'react'

const TIER_BADGES = {
  GOOD: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  REVIEW: 'bg-amber-100 text-amber-900 border-amber-300',
  LOW: 'bg-rose-100 text-rose-900 border-rose-300',
}

export default function OCRBlockTable({
  blocks = [],
  selectedBlockId,
  hoveredBlockId,
  onSelectBlock,
  onHoverBlock,
}) {
  const [tierFilter, setTierFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [copiedAll, setCopiedAll] = useState(false)
  const [copiedId, setCopiedId] = useState(null)

  const filteredBlocks = useMemo(() => {
    return blocks.filter((b) => {
      const tierMatch = tierFilter === 'ALL' || b.confidence_tier === tierFilter
      const textMatch =
        !searchQuery.trim() ||
        b.raw_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.normalized_text.toLowerCase().includes(searchQuery.toLowerCase())
      return tierMatch && textMatch
    })
  }, [blocks, tierFilter, searchQuery])

  const handleCopyAll = () => {
    const fullText = blocks.map((b) => b.normalized_text || b.raw_text).join('\n')
    navigator.clipboard.writeText(fullText)
    setCopiedAll(true)
    setTimeout(() => setCopiedAll(false), 2000)
  }

  const handleCopyBlock = (text, id, e) => {
    e.stopPropagation()
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1500)
  }

  if (!blocks || blocks.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-stone-500 bg-stone-50 rounded border border-stone-200">
        No text blocks recognized in this evidence image.
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-lg shadow-sm overflow-hidden text-xs">
      {/* Controls Bar */}
      <div className="p-3 bg-stone-100 border-b border-stone-200 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Search Input */}
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search recognized text…"
            className="px-2.5 py-1 text-xs border border-stone-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-emerald-700 w-40 sm:w-48"
          />

          {/* Tier Filter */}
          <div className="flex rounded border border-stone-300 overflow-hidden bg-white text-[11px]">
            {['ALL', 'GOOD', 'REVIEW', 'LOW'].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTierFilter(t)}
                className={`px-2 py-1 font-semibold transition-colors ${
                  tierFilter === t
                    ? 'bg-stone-800 text-white'
                    : 'text-stone-600 hover:bg-stone-100'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Copy All Action */}
        <button
          type="button"
          onClick={handleCopyAll}
          className="w-auto px-3 py-1 bg-stone-200 hover:bg-stone-300 text-stone-800 font-semibold rounded text-[11px] flex items-center gap-1 transition-colors"
        >
          {copiedAll ? '✓ Copied All Text' : '📋 Copy All Text'}
        </button>
      </div>

      {/* Block List Table */}
      <div className="flex-1 overflow-y-auto max-h-[420px] divide-y divide-stone-200">
        {filteredBlocks.length === 0 ? (
          <div className="p-6 text-center text-stone-400 italic">
            No blocks match the current filter criteria.
          </div>
        ) : (
          filteredBlocks.map((block, idx) => {
            const isSelected = selectedBlockId === block.id
            const isHovered = hoveredBlockId === block.id
            const isActive = isSelected || isHovered
            const tierBadge = TIER_BADGES[block.confidence_tier] || TIER_BADGES.GOOD

            return (
              <div
                key={block.id || idx}
                onClick={() => onSelectBlock?.(block)}
                onMouseEnter={() => onHoverBlock?.(block.id)}
                onMouseLeave={() => onHoverBlock?.(null)}
                className={`p-3 transition-colors cursor-pointer flex items-start justify-between gap-3 ${
                  isActive
                    ? 'bg-emerald-50/80 border-l-4 border-l-emerald-700'
                    : 'hover:bg-stone-50'
                }`}
              >
                {/* Index / Reading Order Badge */}
                <div className="flex items-center gap-2 pt-0.5">
                  <span className="font-mono text-[10px] font-bold bg-stone-200 text-stone-700 rounded px-1.5 py-0.5 min-w-[22px] text-center">
                    #{(block.reading_order !== undefined && block.reading_order !== null ? block.reading_order : idx) + 1}
                  </span>
                </div>

                {/* Text Content */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-stone-900 text-xs break-words select-text">
                    {block.raw_text}
                  </div>
                  {block.normalized_text && block.normalized_text !== block.raw_text && (
                    <div className="text-[10px] text-stone-500 font-mono mt-0.5 truncate">
                      Norm: {block.normalized_text}
                    </div>
                  )}

                  {/* Bounding Box Coordinates Tag */}
                  {block.bounding_box && (
                    <div className="text-[9px] text-stone-400 font-mono mt-1">
                      Box: [{Math.round(block.bounding_box.x)}, {Math.round(block.bounding_box.y)},{' '}
                      {Math.round(block.bounding_box.width)}×{Math.round(block.bounding_box.height)}]
                    </div>
                  )}
                </div>

                {/* Confidence & Actions */}
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-bold border ${tierBadge}`}
                  >
                    {(block.confidence * 100).toFixed(1)}% {block.confidence_tier}
                  </span>

                  <button
                    type="button"
                    title="Copy this block"
                    onClick={(e) => handleCopyBlock(block.raw_text, block.id, e)}
                    className="w-auto text-[10px] text-stone-400 hover:text-stone-700 p-0.5 bg-transparent"
                  >
                    {copiedId === block.id ? '✓ Copied' : '📋'}
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Table Footer Stats */}
      <div className="p-2 bg-stone-50 border-t border-stone-200 text-[10px] text-stone-500 flex justify-between items-center px-3 font-mono">
        <span>
          Showing {filteredBlocks.length} of {blocks.length} recognized text blocks
        </span>
        <span>
          Avg: {(blocks.reduce((acc, b) => acc + b.confidence, 0) / (blocks.length || 1) * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  )
}
