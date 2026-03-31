'use client'
/**
 * TelegramAuthSection.tsx — авторизация через 6-значный код.
 *
 * Новый поток:
 *  1. Нажать «Войти» → POST /auth/code/request → получить code + session_id
 *  2. Показать пользователю код
 *  3. Пользователь открывает бота и отправляет код
 *  4. Бот спрашивает «Подтвердить?» → пользователь жмёт «Да»
 *  5. Фронт polling-ом GET /auth/code/poll/{session_id} получает JWT
 *  6. Страница обновляется — пользователь вошёл
 *
 * Никаких редиректов. Никакого копирования ссылок.
 * Работает из нативного приложения, мобильного Telegram, десктопа.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { LogOut, Shield, Copy, Check, RefreshCw } from 'lucide-react'
import { logout, type TgUserInfo, setToken } from '@/lib/auth'
import { useScheduleStore } from '@/lib/store'

const BOT_USERNAME = process.env.NEXT_PUBLIC_TG_BOT_USERNAME || 'ncfu_schedule_bot'
const AUTH_BASE    = (process.env.NEXT_PUBLIC_API_URL || '') + '/auth'
const REFRESH_KEY  = 'ncfu_refresh_token'

const ROLE_META: Record<string, { label: string; color: string }> = {
  admin:     { label: 'Администратор', color: '#ef4444' },
  moderator: { label: 'Модератор',     color: '#f97316' },
  vip:       { label: 'VIP',           color: '#eab308' },
  beta:      { label: 'Бета',          color: '#3b82f6' },
  user:      { label: 'Пользователь',  color: '#8e8e93' },
}

type LoginState =
  | 'idle'          // не авторизован, кнопка «Войти»
  | 'loading'       // запрашиваем код
  | 'code_shown'    // показываем код, ждём действий пользователя
  | 'code_matched'  // бот нашёл сессию, ждём подтверждения
  | 'success'       // подтверждено — получили токены
  | 'error'
  | 'expired'       // код истёк

interface Props {
  user:  TgUserInfo | null
  token: string | null
}

export function TelegramAuthSection({ user, token }: Props) {
  const router = useRouter()
  const { setTgUser, setAuthToken, setTgAuthReady, applyServerSettings, setFavorites } =
    useScheduleStore()

  const [loginState,  setLoginState]  = useState<LoginState>('idle')
  const [code,        setCode]        = useState('')
  const [sessionId,   setSessionId]   = useState('')
  const [expiresIn,   setExpiresIn]   = useState(0)
  const [copied,      setCopied]      = useState(false)
  const [error,       setError]       = useState<string | null>(null)

  const pollRef     = useRef<boolean>(false)
  const timerRef    = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollAbort   = useRef<AbortController | null>(null)

  // ── Таймер обратного отсчёта ─────────────────────────────────────────────

  useEffect(() => {
    if (loginState !== 'code_shown' && loginState !== 'code_matched') {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }
    timerRef.current = setInterval(() => {
      setExpiresIn(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current!)
          setLoginState('expired')
          stopPolling()
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [loginState])

  // ── Polling ───────────────────────────────────────────────────────────────

  function stopPolling() {
    pollRef.current = false
    pollAbort.current?.abort()
  }

  async function startPolling(sid: string) {
    pollRef.current = true

    while (pollRef.current) {
      try {
        pollAbort.current = new AbortController()
        const res = await fetch(`${AUTH_BASE}/code/poll/${sid}`, {
          signal: pollAbort.current.signal,
        })

        if (!res.ok) {
          if (res.status === 404) {
            setLoginState('expired')
            return
          }
          // Временная ошибка сети — ждём и повторяем
          await sleep(3000)
          continue
        }

        const data = await res.json()

        if (data.status === 'code_matched') {
          setLoginState('code_matched')
        }

        if (data.status === 'confirmed' && data.access_token) {
          pollRef.current = false
          await handleTokens(data.access_token, data.refresh_token)
          return
        }

        if (data.status === 'pending' && data.expires_in === 0) {
          // Poll timeout — переспрашиваем сразу
          continue
        }

      } catch (err: any) {
        if (err?.name === 'AbortError') return
        await sleep(3000)
      }
    }
  }

  async function handleTokens(accessToken: string, refreshToken: string) {
    // Сохраняем токены
    if (typeof window !== 'undefined') {
      localStorage.setItem(REFRESH_KEY, refreshToken)
    }
    // ВАЖНО: устанавливаем токен в двух местах:
    // 1. auth.ts._token — используется getToken() / getAuthHeader() / authedFetch во всех компонентах
    // 2. store.authToken — используется для реактивных проверок в UI (enabled: !!authToken)
    setToken(accessToken)      // auth.ts module-level variable
    setAuthToken(accessToken)  // zustand store

    // Загружаем данные пользователя
    try {
      const [meRes, settingsRes, favsRes] = await Promise.all([
        fetch(`${AUTH_BASE}/me`, { headers: { Authorization: `Bearer ${accessToken}` } }),
        fetch((process.env.NEXT_PUBLIC_API_URL || '') + '/miniapp/api/settings',
              { headers: { Authorization: `Bearer ${accessToken}` } }),
        fetch((process.env.NEXT_PUBLIC_API_URL || '') + '/miniapp/api/favorites',
              { headers: { Authorization: `Bearer ${accessToken}` } }),
      ])

      if (meRes.ok) {
        const me = await meRes.json()
        setTgUser(me)
      }
      if (settingsRes.ok) {
        const settings = await settingsRes.json()
        applyServerSettings(settings)
      }
      if (favsRes.ok) {
        const { favorites = [] } = await favsRes.json().catch(() => ({ favorites: [] }))
        if (favorites.length) setFavorites(favorites)
      }
    } catch { /* нкрит */ }

    setTgAuthReady(true)
    setLoginState('success')

    // Небольшая пауза — показываем «✅ Вход выполнен» — потом убираем форму
    await sleep(1500)
    router.refresh()
  }

  // ── Запросить код ─────────────────────────────────────────────────────────

  const requestCode = useCallback(async () => {
    setLoginState('loading')
    setError(null)
    setCode('')
    setSessionId('')
    stopPolling()

    try {
      const res = await fetch(`${AUTH_BASE}/code/request`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Ошибка ${res.status}`)
      }
      const data = await res.json()
      setCode(data.code)
      setSessionId(data.session_id)
      setExpiresIn(data.expires_in)
      setLoginState('code_shown')
      startPolling(data.session_id)
    } catch (e: any) {
      setError(e.message || 'Не удалось получить код')
      setLoginState('error')
    }
  }, [])

  // ── Отмена ────────────────────────────────────────────────────────────────

  const cancelLogin = useCallback(async () => {
    stopPolling()
    if (sessionId) {
      fetch(`${AUTH_BASE}/code/cancel/${sessionId}`, { method: 'DELETE' }).catch(() => {})
    }
    setLoginState('idle')
    setCode('')
    setSessionId('')
  }, [sessionId])

  // ── Копировать код ────────────────────────────────────────────────────────

  const copyCode = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard blocked */ }
  }, [code])

  // ── Logout ────────────────────────────────────────────────────────────────

  const handleLogout = useCallback(() => {
    logout()           // чистит auth.ts._token + localStorage refresh
    setAuthToken(null) // чистит store
    setTgUser(null)
    setTgAuthReady(false)
  }, [setAuthToken, setTgUser, setTgAuthReady])

  // Cleanup при размонтировании
  useEffect(() => () => { stopPolling() }, [])

  // ── Авторизован ──────────────────────────────────────────────────────────
  if (user && token) {
    const displayName  = [user.first_name, user.last_name].filter(Boolean).join(' ')
    const nonUserRoles = user.roles.filter(r => r !== 'user')

    return (
      <div className="card px-5 py-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="relative shrink-0">
            {user.photo_url
              ? <img src={user.photo_url} alt={displayName}
                  className="w-11 h-11 rounded-full object-cover"
                  style={{ border: '2px solid rgba(92,225,230,0.4)' }}
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
              : <div className="w-11 h-11 rounded-full flex items-center justify-center text-base font-bold"
                  style={{ background: 'var(--cyan-dim)', border: '2px solid rgba(92,225,230,0.3)', color: 'var(--cyan)' }}>
                  {user.first_name[0]?.toUpperCase()}
                </div>
            }
            <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full flex items-center justify-center"
              style={{ background: '#2AABEE' }}>
              <TelegramIcon />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold truncate" style={{ color: 'var(--t-primary)' }}>
                {displayName}
              </span>
              {nonUserRoles.map(role => {
                const meta = ROLE_META[role] ?? { label: role, color: '#8e8e93' }
                return (
                  <span key={role} className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                    style={{ background: `${meta.color}22`, color: meta.color, border: `1px solid ${meta.color}33` }}>
                    {meta.label}
                  </span>
                )
              })}
            </div>
            {user.username && (
              <div className="text-xs" style={{ color: 'var(--t-muted)' }}>@{user.username}</div>
            )}
          </div>

          <button onClick={handleLogout}
            className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs hover:bg-white/5"
            style={{ color: '#ef4444', border: '1px solid #ef444430' }}>
            <LogOut size={12} />
            Выйти
          </button>
        </div>
      </div>
    )
  }

  // ── Успех ─────────────────────────────────────────────────────────────────
  if (loginState === 'success') {
    return (
      <div className="card px-5 py-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: '#4ade8022' }}>
            <Check size={20} style={{ color: '#4ade80' }} />
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: '#4ade80' }}>Вход выполнен!</p>
            <p className="text-xs" style={{ color: 'var(--t-muted)' }}>Обновляем страницу...</p>
          </div>
        </div>
      </div>
    )
  }

  // ── Показываем код ────────────────────────────────────────────────────────
  if (loginState === 'code_shown' || loginState === 'code_matched') {
    const mm = String(Math.floor(expiresIn / 60)).padStart(2, '0')
    const ss = String(expiresIn % 60).padStart(2, '0')
    const isMatched = loginState === 'code_matched'
    const botUrl = `https://t.me/${BOT_USERNAME}`

    return (
      <div className="card px-5 py-4 mb-4">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>
            Вход через Telegram
          </p>
          <button onClick={cancelLogin} className="text-xs hover:opacity-70"
            style={{ color: 'var(--t-muted)' }}>
            Отмена
          </button>
        </div>

        {/* Инструкция */}
        <div className="flex flex-col gap-3 mb-4">
          <Step n={1} done={false} text={<>Откройте <a href={botUrl} target="_blank" rel="noopener noreferrer"
            className="underline" style={{ color: 'var(--cyan)' }}>@{BOT_USERNAME}</a></>} />
          <Step n={2} done={false} text={<>Отправьте боту: <code style={{ color: 'var(--cyan)', fontFamily: 'monospace' }}>/code {code}</code></>} />
          <Step n={3} done={isMatched} text={isMatched ? "Подтвердите в боте — почти готово!" : "Нажмите «Подтвердить» в боте"} />
        </div>

        {/* Код */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 flex items-center justify-center py-4 rounded-2xl"
            style={{ background: 'var(--surface)', border: '2px solid var(--cyan)33' }}>
            <span className="text-4xl font-bold tracking-[0.3em] font-mono"
              style={{ color: 'var(--cyan)', letterSpacing: '0.3em' }}>
              {code}
            </span>
          </div>
          <button onClick={copyCode}
            className="flex flex-col items-center gap-1 px-3 py-3 rounded-xl hover:bg-white/5"
            style={{ border: '1px solid var(--border)', color: copied ? '#4ade80' : 'var(--t-muted)' }}>
            {copied ? <Check size={16} /> : <Copy size={16} />}
            <span className="text-[9px]">{copied ? 'Скопирован' : 'Копировать'}</span>
          </button>
        </div>

        {/* Таймер + статус */}
        <div className="flex items-center justify-between">
          {isMatched
            ? <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#4ade80' }} />
                <span className="text-xs" style={{ color: '#4ade80' }}>Ожидаем подтверждения в боте...</span>
              </div>
            : <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--cyan)' }} />
                <span className="text-xs" style={{ color: 'var(--t-muted)' }}>Ожидаем код от бота...</span>
              </div>
          }
          <span className="text-xs font-mono" style={{ color: expiresIn < 30 ? '#ef4444' : 'var(--t-muted)' }}>
            {mm}:{ss}
          </span>
        </div>
      </div>
    )
  }

  // ── Истёк ─────────────────────────────────────────────────────────────────
  if (loginState === 'expired') {
    return (
      <div className="card px-5 py-4 mb-4">
        <p className="text-sm text-center mb-3" style={{ color: 'var(--t-muted)' }}>
          Код истёк
        </p>
        <button onClick={requestCode}
          className="w-full py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
          style={{ background: 'var(--cyan)', color: '#000' }}>
          <RefreshCw size={14} />
          Получить новый код
        </button>
      </div>
    )
  }

  // ── Загрузка ──────────────────────────────────────────────────────────────
  if (loginState === 'loading') {
    return (
      <div className="card px-5 py-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: 'var(--cyan-dim)' }}>
            <div className="w-4 h-4 border-2 rounded-full animate-spin"
              style={{ borderColor: 'var(--cyan)', borderTopColor: 'transparent' }} />
          </div>
          <span className="text-sm" style={{ color: 'var(--t-muted)' }}>Генерируем код...</span>
        </div>
      </div>
    )
  }

  // ── Не авторизован (idle / error) ─────────────────────────────────────────
  return (
    <div className="card px-5 py-4 mb-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--cyan-dim)' }}>
            <Shield size={15} style={{ color: 'var(--cyan)' }} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>
              Войти через Telegram
            </div>
            <div className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
              Синхронизация настроек и избранного
            </div>
          </div>
        </div>

        <button onClick={requestCode}
          className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold hover:opacity-80"
          style={{ background: '#2AABEE', color: '#fff' }}>
          <TelegramIcon />
          Войти
        </button>
      </div>

      {loginState === 'error' && error && (
        <div className="mt-3 text-xs px-3 py-2 rounded-lg flex items-center justify-between"
          style={{ background: '#ef444415', color: '#ef4444', border: '1px solid #ef444425' }}>
          <span>{error}</span>
          <button onClick={requestCode} className="underline opacity-80">Повторить</button>
        </div>
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Step({ n, done, text }: { n: number; done: boolean; text: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5"
        style={{
          background: done ? '#4ade8022' : 'var(--surface)',
          border:     `1px solid ${done ? '#4ade8055' : 'var(--border)'}`,
          color:      done ? '#4ade80' : 'var(--t-muted)',
        }}>
        {done ? '✓' : n}
      </div>
      <span className="text-sm leading-5" style={{ color: done ? 'var(--t-secondary)' : 'var(--t-primary)' }}>
        {text}
      </span>
    </div>
  )
}

function TelegramIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.941z"/>
    </svg>
  )
}

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
