'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, RefreshCw, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/api/ecampus'

async function authedFetch(path: string, options: RequestInit = {}) {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Error ${res.status}`)
  }
  return res.json()
}

interface EcampusUser {
  tg_id: number
  username: string | null
  first_name: string | null
  last_name: string | null
  sync_status: string | null
  last_sync: string | null
  courses_count: number
  error_msg: string | null
}

const STATUS_STYLE: Record<string, { color: string; icon: React.ReactNode }> = {
  ok:      { color: '#a6e3a1', icon: <CheckCircle size={10} /> },
  running: { color: '#89b4fa', icon: <Loader2 size={10} className="animate-spin" /> },
  error:   { color: '#f38ba8', icon: <AlertCircle size={10} /> },
}

export function ECampusAdminSection({ token }: { token: string | null }) {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery<{ users: EcampusUser[]; total: number }>({
    queryKey: ['ecampus-admin-users'],
    queryFn: () => authedFetch('/admin/users'),
    enabled: !!token && open,
    staleTime: 30_000,
  })

  const syncAll = useMutation({
    mutationFn: () => authedFetch('/admin/sync-all', { method: 'POST' }),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ['ecampus-admin-users'] }), 3000)
    },
  })

  if (!token) return null

  return (
    <div className="card px-5 py-4 mb-4">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Users size={15} style={{ color: 'var(--accent)' }} />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>
            eCampus — пользователи
          </span>
          {data && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full"
              style={{ background: 'var(--surface)', color: 'var(--t-muted)' }}>
              {data.total}
            </span>
          )}
        </div>
        {open ? <ChevronUp size={14} style={{ color: 'var(--t-muted)' }} />
               : <ChevronDown size={14} style={{ color: 'var(--t-muted)' }} />}
      </button>

      {open && (
        <div className="mt-3">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
              {isLoading ? 'Загрузка...' : error ? 'Ошибка загрузки' : `${data?.total ?? 0} подключений`}
            </span>
            <button
              onClick={() => syncAll.mutate()}
              disabled={syncAll.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs disabled:opacity-50 hover:bg-white/5 transition-all"
              style={{ color: 'var(--accent)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}>
              <RefreshCw size={11} className={syncAll.isPending ? 'animate-spin' : ''} />
              {syncAll.isPending ? 'Запускаю...' : syncAll.isSuccess ? 'Запущено ✓' : 'Синх. всех'}
            </button>
          </div>

          {isLoading && (
            <div className="flex justify-center py-4">
              <Loader2 size={18} className="animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          )}

          {data?.users && data.users.length > 0 && (
            <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto">
              {data.users.map(u => {
                const s = STATUS_STYLE[u.sync_status ?? ''] ?? { color: 'var(--t-muted)', icon: null }
                const name = [u.first_name, u.last_name].filter(Boolean).join(' ') || `tg:${u.tg_id}`
                return (
                  <div key={u.tg_id}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl"
                    style={{ background: 'var(--surface)' }}>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-medium truncate" style={{ color: 'var(--t-primary)' }}>
                        {name}
                      </p>
                      <p className="text-[10px]" style={{ color: 'var(--t-muted)' }}>
                        {u.username ? `@${u.username} · ` : ''}{u.courses_count} предм.
                        {u.last_sync && ` · ${new Date(u.last_sync).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0" style={{ color: s.color }}>
                      {s.icon}
                      <span className="text-[10px]">{u.sync_status ?? '—'}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {data?.users.length === 0 && (
            <p className="text-xs text-center py-4" style={{ color: 'var(--t-muted)' }}>
              Нет подключённых пользователей
            </p>
          )}
        </div>
      )}
    </div>
  )
}
