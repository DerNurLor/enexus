import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, extractError } from '@/api/client'
import { useUIStore, toast } from '@/store/ui'
import { Spinner, EmptyState, SectionHeader } from '@/components/common'
import type { SystemSettings } from '@/types'

const WRITABLE_KEYS = new Set([
  'scrape_interval_hours', 'scraper_concurrency', 'scraper_request_delay',
  'scrape_mode', 'academic_year_start',
  'rate_limit_user_rpm', 'rate_limit_anon_rpm', 'rate_limit_bot_rpm', 'rate_limit_window',
  'cache_ttl_now', 'cache_ttl_day', 'cache_ttl_week', 'cache_ttl_search', 'cache_ttl_meta',
  'activity_log_ttl_days', 'cleanup_hour_utc', 'log_level',
])

const SETTINGS_GROUPS: Record<string, string[]> = {
  'Парсинг': ['scrape_interval_hours', 'scraper_concurrency', 'scraper_request_delay', 'scrape_mode', 'academic_year_start'],
  'Rate Limiting': ['rate_limit_user_rpm', 'rate_limit_anon_rpm', 'rate_limit_bot_rpm', 'rate_limit_window'],
  'Кэш TTL': ['cache_ttl_now', 'cache_ttl_day', 'cache_ttl_week', 'cache_ttl_search', 'cache_ttl_meta'],
  'Логи': ['activity_log_ttl_days', 'cleanup_hour_utc', 'log_level', 'app_env'],
  'Статус': ['telegram_bot_configured', 'openai_configured', 'sentry_configured', 'redis_password_configured', 'mongo_auth_configured'],
}

export function PanelSettings() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [edited, setEdited] = useState<Partial<SystemSettings>>({})
  const [saving, setSaving] = useState(false)

  const { data: cfg, isLoading, error } = useQuery({
    queryKey: ['settings', refreshKey],
    queryFn: () => api.getSettings(),
    staleTime: 30_000,
  })

  function getVal(key: string): unknown {
    return edited[key as keyof SystemSettings] !== undefined
      ? edited[key as keyof SystemSettings]
      : cfg?.[key as keyof SystemSettings]
  }

  function setVal(key: string, value: unknown) {
    setEdited((prev) => ({ ...prev, [key]: value }))
  }

  async function save() {
    if (!Object.keys(edited).length) { toast.info('Нет изменений'); return }
    setSaving(true)
    try {
      const res = await api.saveSettings(edited as Partial<SystemSettings>)
      toast.ok(`Сохранено: ${res.changed.join(', ')}`)
      setEdited({})
    } catch (e) { toast.err(extractError(e)) }
    setSaving(false)
  }

  if (isLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner lg /></div>
  if (error) return <EmptyState icon="⚠" text={extractError(error)} />

  const hasDirty = Object.keys(edited).length > 0

  return (
    <div className="anim-up">
      <SectionHeader
        title="Настройки системы"
        actions={
          <button className="btn btn-primary" onClick={save} disabled={saving || !hasDirty}>
            {saving ? <><Spinner /> Сохранение...</> : '✓ Сохранить'}
          </button>
        }
      />
      {hasDirty && (
        <div style={{ padding: '6px 12px', background: 'var(--ghost2)', border: '1px solid var(--line3)', borderRadius: 'var(--rad)', marginBottom: 16, fontSize: 10, color: 'var(--t-60)' }}>
          ⚠ Несохранённые изменения: {Object.keys(edited).join(', ')}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {Object.entries(SETTINGS_GROUPS).map(([group, keys]) => {
          const visibleKeys = keys.filter((k) => k in (cfg ?? {}))
          if (!visibleKeys.length) return null
          return (
            <div key={group} className="card">
              <div className="card-header"><div className="card-title">{group}</div></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {visibleKeys.map((k) => {
                  const v = getVal(k)
                  const editable = WRITABLE_KEYS.has(k)
                  const isFlag = typeof v === 'boolean'
                  const isDirty = k in edited

                  return (
                    <div key={k} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--line)', paddingBottom: 10 }}>
                      <div>
                        <div style={{ fontSize: 11, color: isDirty ? 'var(--t-100)' : 'var(--t-80)', fontFamily: 'var(--mono)' }}>{k}</div>
                        {!editable && <div style={{ fontSize: 9, color: 'var(--t-20)', marginTop: 1 }}>только чтение</div>}
                      </div>
                      {isFlag ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span className={`dot ${v ? 'dot-ok' : 'dot-warn'}`} />
                          <span style={{ fontSize: 10, color: v ? 'var(--t-60)' : 'var(--t-40)' }}>{v ? 'configured' : 'missing'}</span>
                        </div>
                      ) : editable ? (
                        <input
                          className="input"
                          style={{ width: 160, textAlign: 'right', borderColor: isDirty ? 'var(--line3)' : undefined }}
                          value={String(v ?? '')}
                          onChange={(e) => setVal(k, e.target.value)}
                        />
                      ) : (
                        <span style={{ fontSize: 10, color: 'var(--t-60)', fontFamily: 'var(--mono)' }}>{String(v ?? '—')}</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
