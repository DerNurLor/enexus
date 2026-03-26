'use client'
/**
 * TelegramAuthSection.tsx
 *
 * Секция авторизации в профиле для обычного браузера.
 * Показывает:
 *  - если не авторизован: кнопку входа через Telegram Login Widget
 *  - если авторизован: информацию о пользователе (аватар, имя, роли)
 */
import { useState, useCallback } from 'react'
import { LogOut, Shield, User, Clock } from 'lucide-react'
import { TelegramLoginButton, type TelegramAuthData } from './TelegramLoginButton'
import { loginWithWidgetAndInit, logout, type TgUserInfo } from '@/lib/auth'
import { useScheduleStore } from '@/lib/store'

const BOT_USERNAME = process.env.NEXT_PUBLIC_TG_BOT_USERNAME || 'ncfu_schedule_bot'

const ROLE_META: Record<string, { icon: string; label: string; color: string }> = {
  admin:     { icon: '🔴', label: 'Администратор', color: '#ef4444' },
  moderator: { icon: '🟠', label: 'Модератор',     color: '#f97316' },
  vip:       { icon: '🟡', label: 'VIP',           color: '#eab308' },
  beta:      { icon: '🔵', label: 'Бета-тестер',   color: '#3b82f6' },
  user:      { icon: '⚪', label: 'Пользователь',  color: '#8e8e93' },
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric'
  })
}

interface Props {
  user:  TgUserInfo | null
  token: string | null
}

export function TelegramAuthSection({ user, token }: Props) {
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  const { setTgUser, setAuthToken, setTgAuthReady, applyServerSettings, setFavorites } =
    useScheduleStore()

  const handleAuth = useCallback(async (data: TelegramAuthData) => {
    setLoading(true)
    setError(null)
    try {
      const result = await loginWithWidgetAndInit(data)
      setAuthToken(result.token)
      setTgUser(result.user)
      setTgAuthReady(true)
      if (result.settings) applyServerSettings(result.settings)
      if (result.favorites?.length) setFavorites(result.favorites)
    } catch (e: any) {
      setError(e.message || 'Ошибка авторизации')
    } finally {
      setLoading(false)
    }
  }, [setTgUser, setAuthToken, setTgAuthReady, applyServerSettings, setFavorites])

  const handleLogout = useCallback(() => {
    logout()
    setAuthToken(null)
    setTgUser(null)
    setTgAuthReady(false)
  }, [setAuthToken, setTgUser, setTgAuthReady])

  const handleError = useCallback((err: string) => {
    setError(err)
  }, [])

  // ── Авторизован ──────────────────────────────────────────────────────────
  if (user && token) {
    return (
      <div className="card p-4 flex flex-col gap-4">
        {/* Заголовок */}
        <div className="flex items-center gap-2">
          <Shield size={16} style={{ color: 'var(--cyan)' }} />
          <span className="text-sm font-semibold">Аккаунт Telegram</span>
        </div>

        {/* Профиль пользователя */}
        <div className="flex items-center gap-3">
          {/* Аватар */}
          <div className="relative flex-shrink-0">
            {user.photo_url ? (
              <img
                src={user.photo_url}
                alt={user.first_name}
                className="w-14 h-14 rounded-full object-cover"
                style={{ border: '2px solid var(--cyan)' }}
                onError={(e) => {
                  // Fallback на инициалы если аватар не загрузился
                  e.currentTarget.style.display = 'none'
                  e.currentTarget.nextElementSibling?.removeAttribute('style')
                }}
              />
            ) : null}
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold"
              style={{
                background: 'var(--cyan)22',
                border: '2px solid var(--cyan)',
                color: 'var(--cyan)',
                display: user.photo_url ? 'none' : 'flex',
              }}
            >
              {user.first_name[0]?.toUpperCase()}
            </div>
          </div>

          {/* Имя и username */}
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-base truncate">
              {[user.first_name, user.last_name].filter(Boolean).join(' ')}
            </div>
            {user.username && (
              <div className="text-sm" style={{ color: 'var(--t-muted)' }}>
                @{user.username}
              </div>
            )}
            <div className="flex flex-wrap gap-1 mt-1">
              {user.roles.map(role => {
                const meta = ROLE_META[role] ?? { icon: '⚫', label: role, color: '#8e8e93' }
                return (
                  <span
                    key={role}
                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold"
                    style={{
                      background: `${meta.color}22`,
                      color: meta.color,
                      border: `1px solid ${meta.color}44`,
                    }}
                  >
                    {meta.icon} {meta.label}
                  </span>
                )
              })}
            </div>
          </div>
        </div>

        {/* Дополнительная информация */}
        <div className="flex flex-col gap-1.5 text-xs" style={{ color: 'var(--t-muted)' }}>
          <div className="flex items-center gap-1.5">
            <User size={12} />
            <span>ID: {user.tg_id}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock size={12} />
            <span>Зарегистрирован: {formatDate(user.created_at)}</span>
          </div>
        </div>

        {/* Кнопка выхода */}
        <button
          onClick={handleLogout}
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm transition-colors"
          style={{
            background: '#ef444418',
            color: '#ef4444',
            border: '1px solid #ef444430',
          }}
        >
          <LogOut size={14} />
          Выйти из аккаунта
        </button>
      </div>
    )
  }

  // ── Не авторизован ───────────────────────────────────────────────────────
  return (
    <div className="card p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Shield size={16} style={{ color: 'var(--cyan)' }} />
        <span className="text-sm font-semibold">Войти через Telegram</span>
      </div>

      <p className="text-sm" style={{ color: 'var(--t-muted)' }}>
        Авторизуйтесь чтобы синхронизировать настройки, избранное и получать
        персональные рекомендации на всех устройствах.
      </p>

      {/* Преимущества авторизации */}
      <div className="flex flex-col gap-2">
        {[
          'Синхронизация избранных групп и преподавателей',
          'Сохранение темы и настроек оформления',
          'Личный кабинет с вашим профилем Telegram',
        ].map((benefit, i) => (
          <div key={i} className="flex items-start gap-2 text-xs" style={{ color: 'var(--t-secondary)' }}>
            <span style={{ color: 'var(--cyan)' }}>✓</span>
            {benefit}
          </div>
        ))}
      </div>

      {/* Виджет авторизации */}
      <div className="flex justify-center">
        <TelegramLoginButton
          botUsername={BOT_USERNAME}
          onAuth={handleAuth}
          onError={handleError}
          loading={loading}
        />
      </div>

      {error && (
        <div
          className="text-xs text-center px-3 py-2 rounded-lg"
          style={{ background: '#ef444418', color: '#ef4444', border: '1px solid #ef444430' }}
        >
          {error}
        </div>
      )}

      <p className="text-[10px] text-center" style={{ color: 'var(--t-muted)' }}>
        Авторизация безопасна — проверяется цифровой подписью Telegram.
        Мы не получаем доступ к вашим сообщениям.
      </p>
    </div>
  )
}
