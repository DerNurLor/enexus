'use client'
/**
 * PWAInstallBanner — баннер «Установить приложение» для мобильных.
 * Показывается один раз если:
 *   - Браузер поддерживает beforeinstallprompt (Chrome/Edge Android)
 *   - ИЛИ iOS Safari (показываем инструкцию «Поделиться → На экран»)
 *   - PWA ещё не установлен (не запущен в standalone mode)
 *   - Пользователь не закрыл баннер раньше
 */
import { useState, useEffect } from 'react'
import { X, Download } from 'lucide-react'

function isIOS() {
  if (typeof navigator === 'undefined') return false
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
}
function isStandalone() {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as any).standalone === true
}

export function PWAInstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null)
  const [show, setShow]                     = useState(false)
  const [isIos, setIsIos]                   = useState(false)

  useEffect(() => {
    if (isStandalone()) return
    const dismissed = localStorage.getItem('pwa_banner_dismissed')
    if (dismissed) return

    if (isIOS()) {
      setIsIos(true)
      setShow(true)
      return
    }

    const handler = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e)
      setShow(true)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  function dismiss() {
    setShow(false)
    localStorage.setItem('pwa_banner_dismissed', '1')
  }

  async function install() {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    if (outcome === 'accepted') dismiss()
    setDeferredPrompt(null)
  }

  if (!show) return null

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 lg:hidden rounded-2xl px-4 py-3 flex items-center gap-3 shadow-lg"
      style={{ background: 'var(--card)', border: '1px solid color-mix(in srgb, var(--cyan) 30%, transparent)' }}>
      <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: 'color-mix(in srgb, var(--cyan) 15%, transparent)' }}>
        <Download size={16} style={{ color: 'var(--cyan)' }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold" style={{ color: 'var(--t-primary)' }}>Установить приложение</p>
        <p className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
          {isIos
            ? 'Нажмите «Поделиться» → «На экран "Домой"»'
            : 'Работает без интернета, быстрее загружается'}
        </p>
      </div>
      {!isIos && (
        <button onClick={install}
          className="shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors"
          style={{ background: 'var(--cyan)', color: '#000' }}>
          Установить
        </button>
      )}
      <button onClick={dismiss} className="shrink-0 p-1 rounded-lg hover:bg-white/5">
        <X size={14} style={{ color: 'var(--t-muted)' }} />
      </button>
    </div>
  )
}
