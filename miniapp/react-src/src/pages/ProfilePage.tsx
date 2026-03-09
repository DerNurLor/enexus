import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import type { User, QuotaStatus, Settings, Theme } from '../types'
import { useTheme } from '../hooks/useTheme'

interface Props {
  isActive: boolean
  user: User | null
  settings: Settings
  onSettingChange: (key: keyof Settings, value: unknown) => void
  toast: (msg: string) => void
}

export function ProfilePage({ user, settings, onSettingChange, toast, isActive }: Props) {
  const [quota, setQuota] = useState<QuotaStatus | null>(null)
  const [quotaLoading, setQuotaLoading] = useState(true)
  const [supportText, setSupportText] = useState('')
  const [supportCat, setSupportCat] = useState('question')
  const [sending, setSending] = useState(false)
  const { theme, setTheme } = useTheme((settings.theme as Theme) ?? 'auto')

  useEffect(() => {
    api<QuotaStatus>('/miniapp/api/profile/limits')
      .then(d => { setQuota(d); setQuotaLoading(false) })
      .catch(() => setQuotaLoading(false))
  }, [])

  const handleTheme = useCallback((t: Theme) => {
    setTheme(t)
    onSettingChange('theme', t)
  }, [setTheme, onSettingChange])

  const sendSupport = useCallback(async () => {
    const text = supportText.trim()
    if (!text) { toast('Введите текст обращения'); return }
    setSending(true)
    try {
      await api('/miniapp/api/support', {
        method: 'POST',
        body: JSON.stringify({ message: text, category: supportCat }),
      })
      setSupportText('')
      toast('✅ Обращение отправлено')
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    } catch {
      toast('❌ Ошибка. Попробуйте позже')
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
    } finally {
      setSending(false)
    }
  }, [supportText, supportCat, toast])

  const initials = user
    ? ((user.first_name?.[0] ?? '') + (user.last_name?.[0] ?? '')).toUpperCase()
    : '?'

  const pct = quota && quota.cap > 0
    ? Math.min(quota.used / quota.cap * 100, 100)
    : 0

  const barColor = pct >= 100 ? 'var(--red)' : pct >= 70 ? 'var(--amber)' : 'var(--text-secondary)'

  return (
    <div id="page-profile" className={`page${isActive ? " active" : ""}`}>
      <div className="sec-head">ПРОФИЛЬ</div>

      {/* Hero */}
      <div className="profile-hero">
        <div className="profile-avatar">
          {user?.avatar
            ? <img src={user.avatar} alt="" onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
            : initials
          }
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="profile-name">
            {user ? `${user.first_name} ${user.last_name ?? ''}`.trim() : '—'}
          </div>
          <div className="profile-uname">
            {user?.username ? `@${user.username}` : user ? `tg:${user.tg_id}` : '—'}
          </div>
          {user && (
            <div className="profile-tags">
              {user.roles.map(r => (
                <span key={r} className="profile-tag">{r}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quota */}
      <div className="settings-group">
        <div className="settings-group-title">ЛИМИТ ЗАПРОСОВ</div>
        {quotaLoading ? (
          <div style={{ padding: '16px 0', color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--mono)' }}>
            Загрузка…
          </div>
        ) : quota ? (
          <div style={{ paddingTop: 8 }}>
            <div className="flex justify-between items-center" style={{ marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Использовано</span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                {quota.used} / {quota.cap}
              </span>
            </div>
            <div className="quota-bar-wrap">
              <div
                className="quota-bar-fill"
                style={{ width: `${pct}%`, background: barColor }}
              />
            </div>
            <div className="flex justify-between" style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
              <span>{quota.exhausted ? '🔴 Лимит исчерпан' : `Осталось: ${quota.remaining}`}</span>
              <span>{quota.ttl_secs > 0 ? `Сброс через ${Math.floor(quota.ttl_secs / 3600)}ч ${Math.floor((quota.ttl_secs % 3600) / 60)}м` : 'Лимит сброшен'}</span>
            </div>
            {quota.exhausted && (
              <div style={{
                marginTop: 8, padding: '8px 12px', borderRadius: 8,
                background: 'rgba(255,59,59,0.08)', color: 'var(--red)',
                fontSize: 11, textAlign: 'center', fontFamily: 'var(--mono)',
              }}>
                ⏳ Лимит исчерпан. Попробуйте позже.
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: '12px 0', color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--mono)' }}>
            Не удалось загрузить данные
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="settings-group">
        <div className="settings-group-title">НАСТРОЙКИ</div>

        <ToggleRow
          label="Неделя с понедельника"
          desc="Показывать расписание с пн, а не с сегодня"
          checked={!!settings.weekFromMonday}
          onChange={v => onSettingChange('weekFromMonday', v)}
        />

        <ToggleRow
          label="24-часовой формат"
          checked={settings.time24h !== false}
          onChange={v => onSettingChange('time24h', v)}
        />

        <ToggleRow
          label="Компактный вид"
          desc="Меньше деталей на карточке занятия"
          checked={!!settings.compact}
          onChange={v => onSettingChange('compact', v)}
        />

        <div className="setting-row">
          <div>
            <div className="setting-label">Тема оформления</div>
          </div>
          <div className="flex gap-6">
            {(['auto', 'light', 'dark'] as Theme[]).map(t => (
              <button
                key={t}
                className={`theme-btn${theme === t ? ' active' : ''}`}
                onClick={() => handleTheme(t)}
              >
                {t === 'auto' ? 'Авто' : t === 'light' ? '☀' : '🌙'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Support */}
      <div className="settings-group">
        <div className="settings-group-title">ПОДДЕРЖКА</div>
        <div style={{ paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <select
            className="support-select"
            value={supportCat}
            onChange={e => setSupportCat(e.target.value)}
            style={{ paddingLeft: 12 }}
          >
            <option value="question">❓ Вопрос</option>
            <option value="bug">🐛 Баг / Ошибка</option>
            <option value="suggestion">💡 Предложение</option>
            <option value="other">📝 Другое</option>
          </select>
          <textarea
            className="support-textarea"
            placeholder="Опишите вашу проблему или вопрос…"
            value={supportText}
            onChange={e => setSupportText(e.target.value)}
            style={{ paddingLeft: 12 }}
          />
          <button
            className="btn btn-primary"
            onClick={sendSupport}
            disabled={sending}
          >
            {sending ? <span className="spinner" /> : null}
            {sending ? 'Отправка…' : '📨 Отправить'}
          </button>
        </div>
      </div>

      {/* Footer */}
      <div style={{ paddingTop: 16, borderTop: '0.5px solid var(--border)' }}>
        <div className="text-muted" style={{ marginBottom: 12 }}>СКФУ Расписание · v2.0</div>
        <button
          className="btn btn-secondary"
          onClick={() => window.Telegram?.WebApp?.close()}
        >
          Закрыть приложение
        </button>
      </div>
    </div>
  )
}

function ToggleRow({
  label, desc, checked, onChange,
}: {
  label: string
  desc?: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="setting-row">
      <div>
        <div className="setting-label">{label}</div>
        {desc && <div className="setting-desc">{desc}</div>}
      </div>
      <label className="toggle">
        <input
          type="checkbox"
          checked={checked}
          onChange={e => onChange(e.target.checked)}
        />
        <span className="toggle-track" />
      </label>
    </div>
  )
}
