import { useState, useCallback, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { api, extractError } from '@/api/client'
import { useUIStore, toast } from '@/store/ui'
import { Spinner, UserAvatar, StatusBadge, RolePills, Pagination, SkeletonRow, EmptyState, SectionHeader, DetailPanel, CopyBtn } from '@/components/common'
import { Icon } from '@/components/common/Icons'
import { numFmt, timeAgo, fmtDate } from '@/utils/helpers'
import type { AdminUser } from '@/types'

const PG = 50

export function PanelUsers() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [page, setPage] = useState(0)
  const [q, setQ] = useState('')
  const [blockedOnly, setBlockedOnly] = useState(false)
  const [selected, setSelected] = useState<AdminUser | null>(null)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['users', page, q, blockedOnly, refreshKey],
    queryFn: () => api.getUsers({ skip: page * PG, limit: PG, q: q || undefined, blocked_only: blockedOnly || undefined }),
    placeholderData: keepPreviousData,
    staleTime: 15_000,
  })

  const users = data?.users ?? []
  const total = data?.total ?? 0

  async function toggleBlock(u: AdminUser) {
    try {
      const updated = await api.updateUser(u.id, { is_blocked: !u.is_blocked })
      qc.invalidateQueries({ queryKey: ['users'] })
      if (selected?.id === u.id) setSelected(updated)
      toast.ok(updated.is_blocked ? 'Пользователь заблокирован' : 'Разблокирован')
    } catch (e) { toast.err(extractError(e)) }
  }

  return (
    <div className="anim-up">
      <SectionHeader title="Пользователи" />

      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <span style={{ position: 'absolute', left: 8, color: 'var(--t-40)', pointerEvents: 'none' }}><Icon.search /></span>
          <input className="input" style={{ width: 220, paddingLeft: 28 }} placeholder="Поиск..." value={q}
            onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && setPage(0)} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', userSelect: 'none' }}>
          <input type="checkbox" checked={blockedOnly} onChange={(e) => { setBlockedOnly(e.target.checked); setPage(0) }} style={{ accentColor: 'var(--t-80)' }} />
          <span style={{ fontSize: 11, color: 'var(--t-60)' }}>Только заблокированные</span>
        </label>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--t-40)' }}>{total} пользователей</span>
        {isLoading && <Spinner />}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ paddingLeft: 16 }}>Пользователь</th>
                <th>Роли</th>
                <th>Активность</th>
                <th>Запросов/день</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && !users.length
                ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
                : users.map((u: AdminUser) => (
                  <tr key={u.id} onClick={() => setSelected(u)} style={{ cursor: 'pointer' }}>
                    <td style={{ paddingLeft: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <UserAvatar user={u} />
                        <div>
                          <div style={{ fontSize: 11, color: 'var(--t-100)' }}>{u.display}</div>
                          {u.username && <div style={{ fontSize: 9, color: 'var(--t-40)' }}>@{u.username}</div>}
                        </div>
                      </div>
                    </td>
                    <td><RolePills roles={u.roles} /></td>
                    <td style={{ fontSize: 10, color: 'var(--t-40)' }}>{u.last_active ? timeAgo(u.last_active) : '—'}</td>
                    <td style={{ fontSize: 11 }}>{u.quota_cap}</td>
                    <td><StatusBadge blocked={u.is_blocked} /></td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
        {!isLoading && !users.length && <EmptyState text="Пользователи не найдены" />}
      </div>

      <Pagination page={page} total={total} pageSize={PG} onChange={(p) => setPage(p)} />

      <AnimatePresence>
        {selected && (
          <UserDetail
            user={selected}
            onClose={() => setSelected(null)}
            onToggleBlock={() => toggleBlock(selected)}
            onUpdate={(u) => { setSelected(u); qc.invalidateQueries({ queryKey: ['users'] }) }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function UserDetail({ user, onClose, onToggleBlock, onUpdate }: {
  user: AdminUser
  onClose: () => void
  onToggleBlock: () => void
  onUpdate: (u: AdminUser) => void
}) {
  const [detail, setDetail] = useState<{ keys: import('@/types').ApiKey[]; activity: import('@/types').ActivityLog[]; quota: import('@/types').UserQuota | null } | null>(null)
  const [roles, setRoles] = useState(user.roles.join(', '))
  const [dailyLimit, setDailyLimit] = useState(String(user.daily_requests ?? ''))
  const [saving, setSaving] = useState(false)
  const [tab, setTab] = useState<'info' | 'keys' | 'activity'>('info')

  useEffect(() => {
    api.getUserDetail(user.id).then((d) => setDetail({ keys: d.keys, activity: d.activity, quota: d.quota ?? null })).catch(() => {})
    setRoles(user.roles.join(', '))
    setDailyLimit(String(user.daily_requests ?? ''))
  }, [user.id])

  async function saveRoles() {
    setSaving(true)
    try {
      const newRoles = roles.split(',').map((r) => r.trim()).filter(Boolean)
      const updated = await api.updateUser(user.id, { roles: newRoles })
      onUpdate(updated)
      toast.ok('Роли обновлены')
    } catch (e) { toast.err(extractError(e)) }
    setSaving(false)
  }

  async function saveDailyLimit() {
    setSaving(true)
    try {
      const val = dailyLimit.trim() === '' ? undefined : parseInt(dailyLimit, 10)
      const updated = await api.updateUser(user.id, { daily_requests: val })
      onUpdate(updated)
      toast.ok('Лимит обновлён')
    } catch (e) { toast.err(extractError(e)) }
    setSaving(false)
  }

  async function resetQuota() {
    try {
      await api.resetQuota(user.id)
      toast.ok('Использование сброшено')
    } catch (e) { toast.err(extractError(e)) }
  }

  async function revokeAllKeys() {
    try {
      await api.revokeAllKeys(user.id)
      toast.ok('Все ключи отозваны')
      setDetail((d) => d ? { ...d, keys: d.keys.map((k) => ({ ...k, is_revoked: true })) } : d)
    } catch (e) { toast.err(extractError(e)) }
  }

  return (
    <DetailPanel onClose={onClose}>
      <div className="detail-header">
        <UserAvatar user={user} size={32} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, color: 'var(--t-100)' }}>{user.display}</div>
          {user.username && <div style={{ fontSize: 10, color: 'var(--t-40)' }}>@{user.username} · tg:{user.tg_id}</div>}
        </div>
        <button className="btn btn-ghost btn-icon" onClick={onClose}><Icon.close /></button>
        <a href={user.username ? `https://t.me/${user.username}` : `tg://user?id=${user.tg_id}`}
          target="_blank" rel="noopener noreferrer"
          className="btn btn-ghost btn-icon" title="Открыть в Telegram" style={{ textDecoration: 'none', fontSize: 14 }}>
          ✈
        </a>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 1, borderBottom: '1px solid var(--line)', flexShrink: 0 }}>
        {(['info', 'keys', 'activity'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: '7px 14px', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: 10, color: tab === t ? 'var(--t-100)' : 'var(--t-40)', borderBottom: tab === t ? '2px solid var(--t-100)' : '2px solid transparent', marginBottom: -1 }}>
            {t === 'info' ? 'Инфо' : t === 'keys' ? 'Ключи' : 'Лог'}
          </button>
        ))}
      </div>

      <div className="detail-body">
        {tab === 'info' && (
          <>
            <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
              <StatusBadge blocked={user.is_blocked} />
              <RolePills roles={user.roles} />
            </div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
              <button className="btn btn-danger" onClick={onToggleBlock}>
                {user.is_blocked ? '↩ Разблокировать' : '🚫 Заблокировать'}
              </button>
              <button className="btn btn-ghost" onClick={revokeAllKeys}>Отозвать ключи</button>
            </div>
            <hr className="divider" />
            <div className="input-group" style={{ marginBottom: 8 }}>
              <div className="input-label">Роли (через запятую)</div>
              <input className="input" value={roles} onChange={(e) => setRoles(e.target.value)} />
            </div>
            <button className="btn btn-ghost w-full" style={{ marginBottom: 12 }} onClick={saveRoles} disabled={saving}>
              {saving ? <><Spinner /> Сохранение...</> : '✓ Сохранить роли'}
            </button>
            <hr className="divider" />
            <div className="input-group" style={{ marginBottom: 8 }}>
              <div className="input-label">Лимит запросов в день</div>
              <input className="input" type="number" min={0} max={100000} placeholder="Глобальный лимит" value={dailyLimit} onChange={(e) => setDailyLimit(e.target.value)} />
            </div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
              <button className="btn btn-ghost" style={{ flex: 1 }} onClick={saveDailyLimit} disabled={saving}>✓ Сохранить</button>
              <button className="btn btn-ghost" onClick={resetQuota} title="Сбросить использование">↺</button>
            </div>
            <hr className="divider" />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                { k: 'AI токенов/мес', v: numFmt(user.monthly_ai_tokens || 0) },
                { k: 'Создан', v: user.created_at ? fmtDate(user.created_at) : '—' },
                { k: 'Активность', v: user.last_active ? timeAgo(user.last_active) : '—' },
              ].map((s, i) => (
                <div key={i} style={{ padding: '8px 10px', background: 'var(--ink-20)', borderRadius: 'var(--rad-md)', border: '1px solid var(--line)' }}>
                  <div style={{ fontSize: 9, color: 'var(--t-40)', marginBottom: 3 }}>{s.k}</div>
                  <div style={{ fontSize: 13, fontFamily: 'var(--serif)', color: 'var(--t-100)' }}>{s.v}</div>
                </div>
              ))}
            </div>
            {detail?.quota && (
              <>
                <hr className="divider" />
                <div style={{ fontSize: 9, color: 'var(--t-40)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Квота сообщений (7ч)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                  {[
                    { k: 'Использовано', v: detail.quota.used },
                    { k: 'Максимум', v: detail.quota.cap },
                    { k: 'Осталось', v: detail.quota.remaining },
                  ].map((s, i) => (
                    <div key={i} style={{ padding: '8px 10px', background: detail.quota!.exhausted ? 'rgba(255,80,80,0.06)' : 'var(--ink-20)', borderRadius: 'var(--rad-md)', border: `1px solid ${detail.quota!.exhausted ? 'rgba(255,80,80,0.2)' : 'var(--line)'}` }}>
                      <div style={{ fontSize: 9, color: 'var(--t-40)', marginBottom: 3 }}>{s.k}</div>
                      <div style={{ fontSize: 13, fontFamily: 'var(--serif)', color: i === 2 && detail.quota!.exhausted ? 'rgb(255,80,80)' : 'var(--t-100)' }}>{s.v}</div>
                    </div>
                  ))}
                </div>
                {detail.quota.ttl_secs > 0 && (
                  <div style={{ fontSize: 9, color: 'var(--t-40)', marginTop: 6 }}>
                    Сбросится через {Math.ceil(detail.quota.ttl_secs / 60)} мин
                  </div>
                )}
                {detail.quota.used === 0 && (
                  <div style={{ fontSize: 9, color: 'var(--t-40)', marginTop: 6 }}>Активности нет — счётчик не запущен</div>
                )}
              </>
            )}
          </>
        )}

        {tab === 'keys' && (
          <div>
            {!detail ? <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}><Spinner /></div>
              : detail.keys.length === 0 ? <EmptyState text="Нет ключей API" />
              : detail.keys.map((k) => (
                <div key={k.id} style={{ padding: '8px 10px', background: 'var(--ink-20)', borderRadius: 'var(--rad)', border: '1px solid var(--line)', marginBottom: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontSize: 10, color: 'var(--t-80)' }}>{k.name}</span>
                    <span style={{ fontSize: 9, color: k.is_revoked ? 'var(--t-20)' : 'var(--t-60)' }}>{k.is_revoked ? 'revoked' : 'active'}</span>
                  </div>
                  <div style={{ fontSize: 9, color: 'var(--t-40)', fontFamily: 'var(--mono)' }}>{k.prefix}... · {k.use_count} uses</div>
                </div>
              ))
            }
          </div>
        )}

        {tab === 'activity' && (
          <div>
            {!detail ? <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}><Spinner /></div>
              : detail.activity.length === 0 ? <EmptyState text="Нет активности" />
              : detail.activity.map((a, i) => (
                <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)', fontSize: 10 }}>
                  <div style={{ color: 'var(--t-80)', marginBottom: 2 }}>{a.action}</div>
                  <div style={{ color: 'var(--t-40)', fontSize: 9 }}>{timeAgo(a.timestamp)} {a.ip ? `· ${a.ip}` : ''}</div>
                </div>
              ))
            }
          </div>
        )}
      </div>
    </DetailPanel>
  )
}
