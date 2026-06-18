import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import type { User, QuotaStatus, Settings, Theme } from '../types'
import { useTheme } from '../hooks/useTheme'
import { useI18n, SUPPORTED_LANGUAGES, LANGUAGE_NAMES } from '../i18n'

interface Props {
  isActive: boolean
  user: User | null
  settings: Settings
  onSettingChange: (key: keyof Settings, value: unknown) => void
  toast: (msg: string) => void
}

export function ProfilePage({ user, settings, onSettingChange, toast, isActive }: Props) {
  const { t, lang, setLang } = useI18n()
  const [quota, setQuota] = useState<QuotaStatus | null>(null)
  const [quotaLoading, setQuotaLoading] = useState(true)
  const [supportText, setSupportText] = useState('')
  const [supportCat, setSupportCat] = useState('question')
  const [sending, setSending] = useState(false)
  const { theme, setTheme } = useTheme((settings.theme as Theme) ?? 'auto')

  const handleLanguage = useCallback((code: string) => {
    setLang(code)
    onSettingChange('language', code)
  }, [setLang, onSettingChange])

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
    if (!text) { toast(t('profile.enter_text')); return }
    setSending(true)
    try {
      await api('/miniapp/api/support', {
        method: 'POST',
        body: JSON.stringify({ message: text, category: supportCat }),
      })
      setSupportText('')
      toast(t('profile.sent_ok'))
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    } catch {
      toast(t('profile.send_error'))
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
    } finally {
      setSending(false)
    }
  }, [supportText, supportCat, toast, t])

  const initials = user
    ? ((user.first_name?.[0] ?? '') + (user.last_name?.[0] ?? '')).toUpperCase()
    : '?'

  const pct = quota && quota.cap > 0
    ? Math.min(quota.used / quota.cap * 100, 100)
    : 0

  const barColor = pct >= 100 ? 'var(--red)' : pct >= 70 ? 'var(--amber)' : 'var(--text-secondary)'

  return (
    <div id="page-profile" className={`page${isActive ? " active" : ""}`}>
      <div className="sec-head">{t('profile.title')}</div>

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
        <div className="settings-group-title">{t('profile.quota_title')}</div>
        {quotaLoading ? (
          <div style={{ padding: '16px 0', color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--mono)' }}>
            {t('common.loading')}
          </div>
        ) : quota ? (
          <div style={{ paddingTop: 8 }}>
            <div className="flex justify-between items-center" style={{ marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t('profile.used')}</span>
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
              <span>{quota.exhausted ? t('profile.quota_exhausted') : t('profile.remaining', { n: quota.remaining })}</span>
              <span>{quota.ttl_secs > 0 ? t('profile.reset_in', { h: Math.floor(quota.ttl_secs / 3600), m: Math.floor((quota.ttl_secs % 3600) / 60) }) : t('profile.reset_done')}</span>
            </div>
            {quota.exhausted && (
              <div style={{
                marginTop: 8, padding: '8px 12px', borderRadius: 8,
                background: 'rgba(255,59,59,0.08)', color: 'var(--red)',
                fontSize: 11, textAlign: 'center', fontFamily: 'var(--mono)',
              }}>
                {t('profile.quota_exhausted_msg')}
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: '12px 0', color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--mono)' }}>
            {t('profile.load_failed')}
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="settings-group">
        <div className="settings-group-title">{t('profile.settings_title')}</div>

        <ToggleRow
          label={t('profile.week_from_monday')}
          desc={t('profile.week_from_monday_desc')}
          checked={!!settings.weekFromMonday}
          onChange={v => onSettingChange('weekFromMonday', v)}
        />

        <ToggleRow
          label={t('profile.format_24h')}
          checked={settings.time24h !== false}
          onChange={v => onSettingChange('time24h', v)}
        />

        <ToggleRow
          label={t('profile.compact_view')}
          desc={t('profile.compact_view_desc')}
          checked={!!settings.compact}
          onChange={v => onSettingChange('compact', v)}
        />

        <div className="setting-row">
          <div>
            <div className="setting-label">{t('profile.theme')}</div>
          </div>
          <div className="flex gap-6">
            {(['auto', 'light', 'dark'] as Theme[]).map(th => (
              <button
                key={th}
                className={`theme-btn${theme === th ? ' active' : ''}`}
                onClick={() => handleTheme(th)}
              >
                {th === 'auto' ? t('profile.theme_auto') : th === 'light' ? '☀' : '🌙'}
              </button>
            ))}
          </div>
        </div>

        <div className="setting-row">
          <div>
            <div className="setting-label">{t('profile.language')}</div>
          </div>
          <select
            value={lang}
            onChange={e => handleLanguage(e.target.value)}
            style={{ maxWidth: 140 }}
          >
            {SUPPORTED_LANGUAGES.map(code => (
              <option key={code} value={code}>{LANGUAGE_NAMES[code]}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Support */}
      <div className="settings-group">
        <div className="settings-group-title">{t('profile.support_title')}</div>
        <div style={{ paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <select
            className="support-select"
            value={supportCat}
            onChange={e => setSupportCat(e.target.value)}
            style={{ paddingLeft: 12 }}
          >
            <option value="question">{t('profile.cat_question')}</option>
            <option value="bug">{t('profile.cat_bug')}</option>
            <option value="suggestion">{t('profile.cat_suggestion')}</option>
            <option value="other">{t('profile.cat_other')}</option>
          </select>
          <textarea
            className="support-textarea"
            placeholder={t('profile.support_placeholder')}
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
            {sending ? t('profile.sending') : t('profile.send_button')}
          </button>
        </div>
      </div>

      {/* Footer */}
      <div style={{ paddingTop: 16, borderTop: '0.5px solid var(--border)' }}>
        <div className="text-muted" style={{ marginBottom: 12 }}>{t('profile.footer_brand')}</div>
        <button
          className="btn btn-secondary"
          onClick={() => window.Telegram?.WebApp?.close()}
        >
          {t('profile.close_app')}
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
