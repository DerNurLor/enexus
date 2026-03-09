import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, extractError } from '@/api/client'
import { useUIStore } from '@/store/ui'
import { Spinner, EmptyState, SectionHeader, Pagination, SkeletonRow } from '@/components/common'
import { Icon } from '@/components/common/Icons'
import { timeAgo, fmtDateTime } from '@/utils/helpers'
import type { ActivityLog, ErrorLog } from '@/types'

const PG = 50

// ── Activity Logs ──────────────────────────────────────────────────────────

export function PanelActivity() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [page, setPage] = useState(0)
  const [action, setAction] = useState('')
  const [userId, setUserId] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['activity', page, action, userId, refreshKey],
    queryFn: () => api.getActivityLogs({ action: action || undefined, user_id: userId || undefined, skip: page * PG, limit: PG }),
    keepPreviousData: true,
    staleTime: 15_000,
  })

  const logs = data?.logs ?? []
  const total = data?.total ?? 0

  return (
    <div className="anim-up">
      <SectionHeader title="Журнал активности" />

      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="input" style={{ width: 180 }} placeholder="Фильтр по действию..." value={action} onChange={(e) => { setAction(e.target.value); setPage(0) }} />
        <input className="input" style={{ width: 160 }} placeholder="User ID..." value={userId} onChange={(e) => { setUserId(e.target.value); setPage(0) }} />
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--t-40)' }}>{total} записей</span>
        {isLoading && <Spinner />}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead><tr><th style={{ paddingLeft: 16 }}>Действие</th><th>tg_id</th><th>IP</th><th>Детали</th><th>Время</th></tr></thead>
            <tbody>
              {isLoading && !logs.length
                ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
                : logs.map((l) => <ActivityRow key={l.id} log={l} />)
              }
            </tbody>
          </table>
        </div>
        {!isLoading && !logs.length && <EmptyState text="Записей нет" />}
      </div>
      <Pagination page={page} total={total} pageSize={PG} onChange={(p) => setPage(p)} />
    </div>
  )
}

function ActivityRow({ log }: { log: ActivityLog }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <tr onClick={() => setOpen(!open)} style={{ cursor: 'pointer' }}>
        <td style={{ paddingLeft: 16, fontSize: 10, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.action}</td>
        <td style={{ fontSize: 10, color: 'var(--t-40)' }}>{log.tg_id ?? '—'}</td>
        <td style={{ fontSize: 9, color: 'var(--t-40)' }}>{log.ip ?? '—'}</td>
        <td style={{ fontSize: 9, color: 'var(--t-40)' }}>
          {log.details && Object.keys(log.details).length > 0 ? '{ ... }' : '—'}
        </td>
        <td style={{ fontSize: 9, color: 'var(--t-40)', whiteSpace: 'nowrap' }}>{timeAgo(log.timestamp)}</td>
      </tr>
      {open && log.details && (
        <tr>
          <td colSpan={5} style={{ paddingLeft: 16, paddingBottom: 8, background: 'var(--ink-20)' }}>
            <pre style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t-60)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', lineHeight: 1.6 }}>
              {JSON.stringify(log.details, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  )
}

// ── Error Logs ─────────────────────────────────────────────────────────────

export function PanelErrors() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [level, setLevel] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['errors', page, search, level, refreshKey],
    queryFn: () => api.getErrorLogs({ search: search || undefined, level: level || undefined, skip: page * PG, limit: PG }),
    keepPreviousData: true,
    staleTime: 15_000,
  })

  const logs = data?.logs ?? []
  const total = data?.total ?? 0

  const LEVEL_COLOR: Record<string, string> = {
    ERROR: 'var(--t-60)', CRITICAL: 'var(--t-80)', WARNING: 'var(--t-40)', INFO: 'var(--t-20)',
  }

  return (
    <div className="anim-up">
      <SectionHeader title="Журнал ошибок" />
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <span style={{ position: 'absolute', left: 8, color: 'var(--t-40)', pointerEvents: 'none' }}><Icon.search /></span>
          <input className="input" style={{ width: 200, paddingLeft: 28 }} placeholder="Поиск по тексту..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(0) }} />
        </div>
        <select className="input" style={{ width: 120 }} value={level} onChange={(e) => { setLevel(e.target.value); setPage(0) }}>
          <option value="">Все уровни</option>
          <option value="ERROR">ERROR</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="WARNING">WARNING</option>
          <option value="INFO">INFO</option>
        </select>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--t-40)' }}>{total} ошибок</span>
        {isLoading && <Spinner />}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {isLoading && !logs.length
          ? Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton" style={{ height: 48, borderRadius: 4 }} />)
          : logs.map((e) => (
            <div key={e.id} className="card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => setExpanded(expanded === e.id ? null : e.id)}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <span style={{ fontSize: 9, color: LEVEL_COLOR[e.level] ?? 'var(--t-40)', fontFamily: 'var(--mono)', flexShrink: 0, marginTop: 1, letterSpacing: '0.06em' }}>{e.level}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 11, color: 'var(--t-80)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: expanded === e.id ? 'normal' : 'nowrap' }}>{e.message}</div>
                  {expanded === e.id && e.traceback && (
                    <pre style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t-40)', whiteSpace: 'pre-wrap', marginTop: 8, lineHeight: 1.6, wordBreak: 'break-all', background: 'var(--ink-20)', padding: '8px', borderRadius: 'var(--rad)' }}>
                      {e.traceback}
                    </pre>
                  )}
                  {e.user_text && <div style={{ fontSize: 9, color: 'var(--t-60)', marginTop: 4 }}>User: "{e.user_text}"</div>}
                </div>
                <div style={{ flexShrink: 0, textAlign: 'right' }}>
                  <div style={{ fontSize: 9, color: 'var(--t-40)', whiteSpace: 'nowrap' }}>{timeAgo(e.timestamp)}</div>
                  {e.error_id && <div style={{ fontSize: 8, color: 'var(--t-20)', fontFamily: 'var(--mono)', marginTop: 2 }}>{e.error_id}</div>}
                </div>
              </div>
            </div>
          ))
        }
      </div>
      {!isLoading && !logs.length && <EmptyState text="Ошибок нет" />}
      <Pagination page={page} total={total} pageSize={PG} onChange={(p) => setPage(p)} />
    </div>
  )
}
