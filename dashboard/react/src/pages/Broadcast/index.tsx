import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, extractError } from '@/api/client'
import { useUIStore, toast } from '@/store/ui'
import { Spinner, EmptyState, SectionHeader } from '@/components/common'
import { timeAgo } from '@/utils/helpers'

export function PanelBroadcast() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [text, setText] = useState('')
  const [audience, setAudience] = useState<'all' | 'active' | 'role'>('all')
  const [role, setRole] = useState('')
  const [scheduleAt, setScheduleAt] = useState('')
  const [sending, setSending] = useState(false)
  const [preview, setPreview] = useState(false)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['broadcasts', refreshKey],
    queryFn: () => api.getBroadcasts(),
    staleTime: 15_000,
  })

  const broadcasts = data?.broadcasts ?? []

  async function send() {
    if (!text.trim()) { toast.err('Введите текст'); return }
    setSending(true)
    try {
      const res = await api.sendBroadcast({
        text: text.trim(),
        audience,
        role: audience === 'role' ? role : undefined,
        schedule_at: scheduleAt || undefined,
      })
      toast.ok(`Рассылка поставлена в очередь: ${res.job_id}`)
      setText('')
      setScheduleAt('')
      qc.invalidateQueries({ queryKey: ['broadcasts'] })
    } catch (e) { toast.err(extractError(e)) }
    setSending(false)
  }

  const statusColor: Record<string, string> = {
    queued: 'var(--t-60)', sending: 'var(--t-80)', done: 'var(--t-40)', failed: 'var(--t-20)',
  }

  return (
    <div className="anim-up">
      <SectionHeader title="Рассылка" />
      <div className="grid-2-1" style={{ gap: 16 }}>
        {/* Compose */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header"><div className="card-title">Новая рассылка</div></div>
            <div className="input-group" style={{ marginBottom: 10 }}>
              <div className="input-label">Аудитория</div>
              <select className="input" value={audience} onChange={(e) => setAudience(e.target.value as typeof audience)}>
                <option value="all">Все пользователи</option>
                <option value="active">Активные (7 дней)</option>
                <option value="role">По роли</option>
              </select>
            </div>
            {audience === 'role' && (
              <div className="input-group" style={{ marginBottom: 10 }}>
                <div className="input-label">Роль</div>
                <input className="input" value={role} onChange={(e) => setRole(e.target.value)} placeholder="beta, vip..." />
              </div>
            )}
            <div className="input-group" style={{ marginBottom: 10 }}>
              <div className="input-label">Текст сообщения (HTML поддерживается)</div>
              <textarea className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Привет! Новое обновление..." style={{ minHeight: 120 }} />
            </div>
            <div className="input-group" style={{ marginBottom: 14 }}>
              <div className="input-label">Запланировать (опционально)</div>
              <input className="input" type="datetime-local" value={scheduleAt} onChange={(e) => setScheduleAt(e.target.value)} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={send} disabled={sending || !text.trim()}>
                {sending ? <><Spinner /> Отправка...</> : '📡 Отправить рассылку'}
              </button>
              <button className="btn btn-ghost" onClick={() => setPreview(!preview)}>
                {preview ? 'Скрыть' : 'Предпросмотр'}
              </button>
            </div>
          </div>
          {preview && text && (
            <div className="card">
              <div className="card-header"><div className="card-title">Предпросмотр</div></div>
              <div style={{ background: 'var(--ink-20)', borderRadius: 'var(--rad)', padding: '10px 12px', fontSize: 11, lineHeight: 1.6, color: 'var(--t-80)' }}
                dangerouslySetInnerHTML={{ __html: text }} />
            </div>
          )}
        </div>

        {/* History */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">История рассылок</div>
            {isLoading && <Spinner />}
          </div>
          {broadcasts.length === 0
            ? <EmptyState text="Рассылок пока нет" />
            : broadcasts.map((b) => (
              <div key={b.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                  <span style={{ fontSize: 10, color: 'var(--t-80)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>{b.text.slice(0, 60)}...</span>
                  <span style={{ fontSize: 9, color: statusColor[b.status] ?? 'var(--t-40)', flexShrink: 0, textTransform: 'uppercase' }}>{b.status}</span>
                </div>
                <div style={{ fontSize: 9, color: 'var(--t-40)' }}>{b.audience} · {b.sent_count} отправлено · {timeAgo(b.created_at)}</div>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  )
}
