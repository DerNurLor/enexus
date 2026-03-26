'use client'
import { useEffect, useRef } from 'react'

export interface TelegramAuthData {
  id: number; first_name: string; last_name?: string
  username?: string; photo_url?: string; auth_date: number; hash: string
}

interface Props {
  botUsername: string
  onAuth: (data: TelegramAuthData) => void
  onError?: (err: string) => void
  loading?: boolean
}

export function TelegramLoginButton({ botUsername, onAuth, onError, loading }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ;(window as any).__onTelegramAuth = onAuth
    return () => { delete (window as any).__onTelegramAuth }
  }, [onAuth])

  useEffect(() => {
    const container = containerRef.current
    if (!container || !botUsername) return

    container.innerHTML = ''

    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-radius', '8')
    script.setAttribute('data-onauth', '__onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    script.async = true
    script.onerror = () => onError?.('Не удалось загрузить виджет')
    container.appendChild(script)

    return () => { container.innerHTML = '' }
  }, [botUsername, onError])

  return (
    <div style={{ opacity: loading ? 0.6 : 1, pointerEvents: loading ? 'none' : 'auto', minHeight: 44 }}>
      <div ref={containerRef} />
    </div>
  )
}
