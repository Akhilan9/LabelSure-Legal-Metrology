import { useEffect, useRef, useState } from 'react'
import AuthorizedImage from './AuthorizedImage'

const CONFIDENCE_COLORS = {
  GOOD: {
    stroke: '#059669',
    fill: 'rgba(16, 185, 129, 0.18)',
    activeStroke: '#047857',
    activeFill: 'rgba(16, 185, 129, 0.40)',
    badgeBg: '#065f46',
    text: '#ffffff',
  },
  REVIEW: {
    stroke: '#d97706',
    fill: 'rgba(245, 158, 11, 0.22)',
    activeStroke: '#b45309',
    activeFill: 'rgba(245, 158, 11, 0.45)',
    badgeBg: '#92400e',
    text: '#ffffff',
  },
  LOW: {
    stroke: '#e11d48',
    fill: 'rgba(225, 29, 72, 0.25)',
    activeStroke: '#be123c',
    activeFill: 'rgba(225, 29, 72, 0.50)',
    badgeBg: '#9f1239',
    text: '#ffffff',
  },
}

export default function OCRBoundingBoxCanvas({
  imageUrl,
  altText,
  blocks = [],
  selectedBlockId,
  hoveredBlockId,
  onSelectBlock,
  onHoverBlock,
  showOverlays = true,
  showLabels = true,
}) {
  const [naturalDimensions, setNaturalDimensions] = useState({ width: 0, height: 0 })
  const [imageLoaded, setImageLoaded] = useState(false)
  const containerRef = useRef(null)

  const handleImageLoad = (e) => {
    if (e.target) {
      setNaturalDimensions({
        width: e.target.naturalWidth || 800,
        height: e.target.naturalHeight || 600,
      })
      setImageLoaded(true)
    }
  }

  const { width: imgW, height: imgH } = naturalDimensions

  return (
    <div className="relative inline-block max-w-full max-h-full select-none" ref={containerRef}>
      {/* Base Image Artifact */}
      <AuthorizedImage
        src={imageUrl}
        alt={altText || 'OCR Evidence Image'}
        onLoad={handleImageLoad}
        className="max-h-[55vh] max-w-full w-auto h-auto object-contain block mx-auto rounded shadow-sm bg-stone-950/5"
      />

      {/* SVG Coordinate Bounding Box Overlay */}
      {showOverlays && imageLoaded && imgW > 0 && imgH > 0 && (
        <svg
          viewBox={`0 0 ${imgW} ${imgH}`}
          className="absolute inset-0 w-full h-full pointer-events-auto"
          style={{ objectFit: 'contain' }}
        >
          {blocks.map((block, idx) => {
            const isSelected = selectedBlockId === block.id
            const isHovered = hoveredBlockId === block.id
            const isActive = isSelected || isHovered

            const tier = block.confidence_tier || (block.confidence >= 0.85 ? 'GOOD' : block.confidence >= 0.60 ? 'REVIEW' : 'LOW')
            const colors = CONFIDENCE_COLORS[tier] || CONFIDENCE_COLORS.GOOD

            // Construct SVG polygon points string from 4-point polygon [[x,y], [x,y], ...]
            const pointsStr = block.polygon && Array.isArray(block.polygon) && block.polygon.length >= 3
              ? block.polygon.map((pt) => `${pt[0]},${pt[1]}`).join(' ')
              : `${block.bounding_box?.x || 0},${block.bounding_box?.y || 0} ` +
                `${(block.bounding_box?.x || 0) + (block.bounding_box?.width || 0)},${block.bounding_box?.y || 0} ` +
                `${(block.bounding_box?.x || 0) + (block.bounding_box?.width || 0)},${(block.bounding_box?.y || 0) + (block.bounding_box?.height || 0)} ` +
                `${block.bounding_box?.x || 0},${(block.bounding_box?.y || 0) + (block.bounding_box?.height || 0)}`

            const firstPoint = (block.polygon && block.polygon[0]) || [block.bounding_box?.x || 0, block.bounding_box?.y || 0]

            return (
              <g
                key={block.id || idx}
                className="cursor-pointer transition-all duration-150"
                onClick={(e) => {
                  e.stopPropagation()
                  onSelectBlock?.(block)
                }}
                onMouseEnter={() => onHoverBlock?.(block.id)}
                onMouseLeave={() => onHoverBlock?.(null)}
              >
                {/* Visual Polygon */}
                <polygon
                  points={pointsStr}
                  fill={isActive ? colors.activeFill : colors.fill}
                  stroke={isActive ? colors.activeStroke : colors.stroke}
                  strokeWidth={isActive ? Math.max(imgW / 350, 3) : Math.max(imgW / 500, 1.5)}
                  strokeDasharray={tier === 'LOW' ? '4 2' : undefined}
                />

                {/* Block Sequence Label Tag (Top-Left of Box) */}
                {showLabels && (
                  <g transform={`translate(${firstPoint[0]}, ${Math.max(firstPoint[1] - (imgW / 80), 12)})`}>
                    <rect
                      x="0"
                      y="-12"
                      width={imgW > 1200 ? 28 : 22}
                      height={imgW > 1200 ? 16 : 13}
                      rx="3"
                      fill={colors.badgeBg}
                      opacity={isActive ? 1 : 0.85}
                    />
                    <text
                      x={imgW > 1200 ? 14 : 11}
                      y="-2"
                      textAnchor="middle"
                      fill={colors.text}
                      fontSize={imgW > 1200 ? '11px' : '9px'}
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      {block.reading_order !== undefined && block.reading_order !== null ? block.reading_order + 1 : idx + 1}
                    </text>
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      )}
    </div>
  )
}
