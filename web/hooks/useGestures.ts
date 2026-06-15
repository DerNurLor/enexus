import { useRef, useCallback } from 'react'

interface GestureConfig {
  onSwipeLeft?:      (velocity: number) => void
  onSwipeRight?:     (velocity: number) => void
  onSwipeUp?:        (velocity: number) => void
  onSwipeDown?:      (velocity: number) => void
  onLongPress?:      (x: number, y: number) => void
  onDoubleTap?:      (x: number, y: number) => void
  onPinchIn?:        (scale: number) => void
  onPinchOut?:       (scale: number) => void
  onEdgeSwipeLeft?:  () => void
  onEdgeSwipeRight?: () => void
  swipeThreshold?:   number
  velocityThreshold?:number
  longPressDelay?:   number
  edgeZone?:         number
  disabled?:         boolean
}

export function useGestures(config: GestureConfig) {
  const {
    swipeThreshold    = 50,
    velocityThreshold = 0.3,
    longPressDelay    = 500,
    edgeZone          = 30,
    disabled          = false,
  } = config

  const t0        = useRef<number>(0)
  const x0        = useRef<number>(0)
  const y0        = useRef<number>(0)
  const x0Edge    = useRef<number>(0)
  const touches0  = useRef<number>(0)
  const dist0     = useRef<number>(0)
  const longTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastTap   = useRef<number>(0)
  const moved     = useRef(false)

  function pinchDist(touches: { [index: number]: { clientX: number; clientY: number }; length: number }) {
    const a = touches[0], b = touches[1]
    if (!a || !b) return 0
    return Math.hypot(b.clientX - a.clientX, b.clientY - a.clientY)
  }

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    if (disabled) return
    const touch = e.touches[0]
    x0.current = touch.clientX; y0.current = touch.clientY
    x0Edge.current = touch.clientX
    t0.current = Date.now()
    touches0.current = e.touches.length
    moved.current = false

    if (e.touches.length === 2) dist0.current = pinchDist(e.touches)

    if (e.touches.length === 1 && config.onLongPress) {
      const cx = touch.clientX, cy = touch.clientY
      longTimer.current = setTimeout(() => {
        if (!moved.current) {
          if ('vibrate' in navigator) navigator.vibrate(30)
          config.onLongPress!(cx, cy)
        }
      }, longPressDelay)
    }
  }, [disabled, longPressDelay]) // eslint-disable-line react-hooks/exhaustive-deps

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (disabled) return
    const dx = Math.abs(e.touches[0].clientX - x0.current)
    const dy = Math.abs(e.touches[0].clientY - y0.current)
    if (dx > 8 || dy > 8) {
      moved.current = true
      if (longTimer.current) { clearTimeout(longTimer.current); longTimer.current = null }
    }
  }, [disabled])

  const onTouchEnd = useCallback((e: React.TouchEvent) => {
    if (disabled) return
    if (longTimer.current) { clearTimeout(longTimer.current); longTimer.current = null }

    const touch = e.changedTouches[0]
    const dx = touch.clientX - x0.current
    const dy = touch.clientY - y0.current
    const dt = Math.max(Date.now() - t0.current, 1)
    const vx = Math.abs(dx) / dt
    const vy = Math.abs(dy) / dt
    const adx = Math.abs(dx), ady = Math.abs(dy)

    if (touches0.current === 2) {
      const scale = pinchDist(e.changedTouches) / (dist0.current || 1)
      if (scale < 0.8 && config.onPinchIn)  config.onPinchIn(scale)
      if (scale > 1.2 && config.onPinchOut) config.onPinchOut(scale)
      return
    }

    if (config.onDoubleTap && adx < 20 && ady < 20) {
      const now = Date.now()
      if (now - lastTap.current < 300) {
        config.onDoubleTap(touch.clientX, touch.clientY)
        lastTap.current = 0; return
      }
      lastTap.current = now
    }

    if (x0Edge.current < edgeZone && dx > swipeThreshold && config.onEdgeSwipeRight) {
      if ('vibrate' in navigator) navigator.vibrate(8)
      config.onEdgeSwipeRight(); return
    }
    if (x0Edge.current > (typeof window !== 'undefined' ? window.innerWidth : 400) - edgeZone && -dx > swipeThreshold && config.onEdgeSwipeLeft) {
      if ('vibrate' in navigator) navigator.vibrate(8)
      config.onEdgeSwipeLeft(); return
    }

    if (adx > ady) {
      if (adx >= swipeThreshold && vx >= velocityThreshold) {
        if (dx < 0 && config.onSwipeLeft)  { if ('vibrate' in navigator) navigator.vibrate(6); config.onSwipeLeft(vx) }
        if (dx > 0 && config.onSwipeRight) { if ('vibrate' in navigator) navigator.vibrate(6); config.onSwipeRight(vx) }
      }
    } else {
      if (ady >= swipeThreshold && vy >= velocityThreshold) {
        if (dy < 0 && config.onSwipeUp)   config.onSwipeUp(vy)
        if (dy > 0 && config.onSwipeDown) config.onSwipeDown(vy)
      }
    }
  }, [disabled, swipeThreshold, velocityThreshold, edgeZone]) // eslint-disable-line react-hooks/exhaustive-deps

  return { onTouchStart, onTouchMove, onTouchEnd }
}
