import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { api } from '../api'
import type { NormalizedROI } from '../types'

const PREVIEW_INTERVAL_MS = 2_000

export function RoiEditor({ cameraId, active, roi, width, height, onChange }: {
  cameraId: number | null
  active: boolean
  roi: NormalizedROI
  width: number
  height: number
  onChange: (roi: NormalizedROI) => void
}) {
  const [nonce, setNonce] = useState(0)
  const [previewReady, setPreviewReady] = useState(false)
  const dragStart = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    if (!cameraId || !active) return
    const timer = window.setInterval(() => setNonce((current) => current + 1), PREVIEW_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [cameraId, active])

  function position(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    return {
      x: Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width)),
      y: Math.min(1, Math.max(0, (event.clientY - bounds.top) / bounds.height)),
    }
  }

  function beginSelection(event: PointerEvent<HTMLDivElement>) {
    const start = position(event)
    dragStart.current = start
    event.currentTarget.setPointerCapture(event.pointerId)
    onChange({ x: start.x, y: start.y, width: 0.01, height: 0.01 })
  }

  function updateSelection(event: PointerEvent<HTMLDivElement>) {
    if (!dragStart.current || !event.currentTarget.hasPointerCapture(event.pointerId)) return
    const current = position(event)
    const x = Math.min(dragStart.current.x, current.x)
    const y = Math.min(dragStart.current.y, current.y)
    onChange({
      x,
      y,
      width: Math.max(0.01, Math.abs(current.x - dragStart.current.x)),
      height: Math.max(0.01, Math.abs(current.y - dragStart.current.y)),
    })
  }

  function finishSelection(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    dragStart.current = null
  }

  const canPreview = cameraId !== null && active
  return <div>
    <div
      className="roi-canvas"
      style={{ aspectRatio: `${width} / ${height}` }}
      onPointerDown={canPreview ? beginSelection : undefined}
      onPointerMove={canPreview ? updateSelection : undefined}
      onPointerUp={finishSelection}
      onPointerCancel={finishSelection}
      aria-label="Canlı görüntü üzerinde ROI seçimi. Klavye için aşağıdaki sayısal alanları kullanın."
    >
      {canPreview && <img
        src={api.cameraPreviewUrl(cameraId, nonce)}
        alt="Kamera önizlemesi"
        width={width}
        height={height}
        onLoad={() => setPreviewReady(true)}
        onError={() => setPreviewReady(false)}
      />}
      {(!canPreview || !previewReady) && <div className="preview-empty">
        <strong>{cameraId ? 'Görüntü bekleniyor' : 'Önce kamerayı kaydedin'}</strong>
        <span>ROI seçimi aktif kameradan frame geldiğinde kullanılabilir.</span>
      </div>}
      {canPreview && previewReady && <span className="roi-box" style={{
        left: `${roi.x * 100}%`, top: `${roi.y * 100}%`,
        width: `${roi.width * 100}%`, height: `${roi.height * 100}%`,
      }}><span>Detection ROI</span></span>}
    </div>
    <p className="field-help">Yeni alanı çizmek için görüntü üzerinde sürükleyin. Değerler çözünürlükten bağımsızdır.</p>
  </div>
}
