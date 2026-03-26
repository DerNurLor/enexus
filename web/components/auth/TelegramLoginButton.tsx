'use client'
/**
 * TelegramLoginButton.tsx
 *
 * Виджет авторизации через Telegram Login Widget для обычного браузера.
 *
 * Поток:
 *  1. Пользователь нажимает кнопку → открывается popup Telegram
 *  2. Пользователь подтверждает авторизацию
 *  3. Telegram вызывает window.__onTelegramAuth(user) с данными пользователя
 *  4. Мы отправляем эти данные на POST /auth/telegram/widget
 *  5. Сервер проверяет hash через HMAC-SHA256 (bot token) и выдаёт JWT
 *
 * Безопасность:
 *  - Проверка hash выполняется на сервере (не на клиенте)
 *  - Данные от Telegram содержат auth_date — сервер отклоняет устаревшие (>86400s)
 *  - access token хранится только в памяти, refresh — в localStorage
 */

import { useEffect, useRef, useCallback } from 'react'
import { MessageCircle } from 'lucide-react'

export interface TelegramAuthData {
  id:         number
  first_name: string
  last_name?: string
  username?:  string
  photo_url?: string
  auth_date:  number
  hash:       string
}

interface Props {
  botUsername: string
  onAuth:      (data: TelegramAuthData) => void
  onError?:    (err: string) => void
  loading?:    boolean
}

export function TelegramLoginButton({ botUsername, onAuth, onError, loading }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const scriptRef    = useRef<HTMLScriptElement | null>(null)

  const handleAuth = useCallback((data: TelegramAuthData) => {
    onAuth(data)
  }, [onAuth])

  useEffect(() => {
    // Регистрируем глобальный callback который вызовет Telegram
    ;(window as any).__onTelegramAuth = handleAuth

    return () => {
      delete (window as any).__onTelegramAuth
    }
  }, [handleAuth])

  useEffect(() => {
    if (!containerRef.current) return

    // Удаляем старый скрипт если есть
    if (scriptRef.current) {
      scriptRef.current.remove()
      scriptRef.current = null
    }

    const script = document.createElement('script')
    script.src           = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login',   botUsername)
    script.setAttribute('data-size',             'large')
    script.setAttribute('data-radius',           '12')
    script.setAttribute('data-onauth',           '__onTelegramAuth(user)')
    script.setAttribute('data-request-access',  'write')
    script.async = true
    script.onerror = () => onError?.('Не удалось загрузить виджет Telegram')

    containerRef.current.appendChild(script)
    scriptRef.current = script

    return () => {
      script.remove()
      scriptRef.current = null
    }
  }, [botUsername, onError])

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Скрываем нативный виджет и показываем свою кнопку поверх */}
      <div className="relative">
        {/* Нативный Telegram виджет (невидимый, но кликабельный) */}
        <div
          ref={containerRef}
          style={{ opacity: loading ? 0.5 : 1, pointerEvents: loading ? 'none' : 'auto' }}
        />
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--t-muted)' }}>
          <div className="w-4 h-4 border-2 rounded-full animate-spin"
            style={{ borderColor: 'var(--cyan)', borderTopColor: 'transparent' }} />
          Выполняется вход...
        </div>
      )}
    </div>
  )
}
