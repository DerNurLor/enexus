'use client'
/**
 * TelegramAuthSection.tsx
 *
 * Авторизация через бота вместо Telegram Login Widget.
 *
 * Поток:
 *  1. Пользователь нажимает «Войти через Telegram»
 *  2. Открывается t.me/ncfu_schedule_bot?start=login
 *  3. Бот отправляет кнопку «Подтвердить вход» → URL /profile?bot_token=OTP
 *  4. Пользователь нажимает → попадает на /profile с ?bot_token=
 *  5. Страница вызывает POST /auth/bot/exchange → получает JWT
 */
import { useState, useCallback, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { LogOut, Shield, ExternalLink } from 'lucide-react'
import { loginWithBotToken, logout, type TgUserInfo } from '@/lib/auth'
import { useScheduleStore } from '@/lib/store'

const BOT_USERNAME = process.env.NEXT_PUBLIC_TG_BOT_USERNAME || 'ncfu_schedule_bot'

const ROLE_META: Record<string, { label: string; color: string }> = {
  admin:     { label: 'Администратор', color: '#ef4444' },
  moderator: { label: 'Модератор',     color: '#f97316' },
  vip:       { label: 'VIP',           color: '#eab308' },
  beta:      { label: 'Бета',          color: '#3b82f6' },
  user:      { label: 'Пользователь',  color: '#8e8e93' },
}

interface Props {
  user:  TgUserInfo | null
  token: string | null
}

export function TelegramAuthSection({ user, token }: Props) {
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)
  const searchParams = useSearchParams()
  const router = useRouter()

  const { setTgUser, setAuthToken, setTgAuthReady, applyServerSettings, setFavorites } =
    useScheduleStore()

  // Обрабатываем ?bot_token= при возврате с бота
  useEffect(() => {
    const botToken = searchParams.get('bot_token')
    if (!botToken || user) return

    setLoading(true)
    setError(null)

    loginWithBotToken(botToken)
      .then(result => {
        setAuthToken(result.token)
        setTgUser(result.user)
        setTgAuthReady(true)
        if (result.settings)          applyServerSettings(result.settings)
        if (result.favorites?.length) setFavorites(result.favorites)
        // Убираем токен из URL
        router.replace('/profile')
      })
      .catch(e => {
        setError(e.message || 'Ошибка авторизации')
        router.replace('/profile')
      })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleLogout = useCallback(() => {
    logout()
    setAuthToken(null)
    setTgUser(null)
    setTgAuthReady(false)
  }, [setAuthToken, setTgUser, setTgAuthReady])

  // ── Авторизован ──────────────────────────────────────────────────────────
  if (user && token) {
    const displayName  = [user.first_name, user.last_name].filter(Boolean).join(' ')
    const nonUserRoles = user.roles.filter(r => r !== 'user')

    return (
      <div className="card px-5 py-4 mb-4">
        <div className="flex items-center gap-3">
          {/* Аватар */}
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
            {/* Иконка Telegram */}
            <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full flex items-center justify-center"
              style={{ background: '#2AABEE' }}>
              <svg width="9" height="9" viewBox="0 0 24 24" fill="white">
                <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.941z"/>
              </svg>
            </div>
          </div>

          {/* Имя и роли */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold truncate" style={{ color: 'var(--t-primary)' }}>
                {displayName}
              </span>
              {nonUserRoles.map(role => {
                const meta = ROLE_META[role] ?? { label: role, color: '#8e8e93' }
                return (
                  <span key={role}
                    className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
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

          {/* Кнопка выхода */}
          <button onClick={handleLogout}
            className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs transition-colors hover:bg-white/5"
            style={{ color: '#ef4444', border: '1px solid #ef444430' }}>
            <LogOut size={12} />
            Выйти
          </button>
        </div>
      </div>
    )
  }

  // ── Идёт авторизация (вернулись с бота) ─────────────────────────────────
  if (loading) {
    return (
      <div className="card px-5 py-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: 'var(--cyan-dim)' }}>
            <div className="w-4 h-4 border-2 rounded-full animate-spin"
              style={{ borderColor: 'var(--cyan)', borderTopColor: 'transparent' }} />
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>
              Выполняется вход...
            </div>
            <div className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
              Проверяем подтверждение от Telegram
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Не авторизован ───────────────────────────────────────────────────────
  const botUrl = `https://t.me/${BOT_USERNAME}?start=login`

  return (
    <div className="card px-5 py-4 mb-4">
      <div className="flex items-center justify-between gap-4">
        {/* Левая часть */}
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

        {/* Кнопка */}
        <a href={botUrl} target="_blank" rel="noopener noreferrer"
          className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all hover:opacity-80"
          style={{ background: '#2AABEE', color: '#fff' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.941z"/>
          </svg>
          Войти
        </a>
      </div>

      {error && (
        <div className="mt-3 text-xs px-3 py-2 rounded-lg"
          style={{ background: '#ef444415', color: '#ef4444', border: '1px solid #ef444425' }}>
          {error}
        </div>
      )}
    </div>
  )
}
