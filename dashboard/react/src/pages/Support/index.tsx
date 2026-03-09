import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, extractError } from '@/api/client'
import { useUIStore, toast } from '@/store/ui'
import { Spinner, EmptyState, SectionHeader, DetailPanel, Pagination } from '@/components/common'
import { Icon } from '@/components/common/Icons'
import { timeAgo, fmtDateTime } from '@/utils/helpers'
import type { SupportTicket } from '@/types'

const STATUS_COLOR: Record<string, string> = {
  open:     'var(--t-60)',
  answered: 'var(--t-80)',
  closed:   'var(--t-20)',
}
const CAT_EMOJI: Record<string, string> = {
  bug: '🐛', suggestion: '💡', question: '❓', other: '📝',
}

const PG = 30

export function PanelSupport() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [page, setPage] = useState(0)
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [selected, setSelected] = useState<SupportTicket | null>(null)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['support', page, status, category, refreshKey],
    queryFn: () => api.getSupportTickets({ status: status || undefined, category: category || undefined, skip: page * PG, limit: PG }),
    keepPreviousData: true,
    staleTime: 15_000,
  })

  const tickets = data?.tickets ?? []
  const total = data?.total ?? 0

  return (
    <div className="anim-up">
      <SectionHeader title="Тикеты поддержки" />

      <div style={{ display: 'flex', gap: 8, marginBottom: 14, alignItems: 'center', flexWrap: 'wrap' }}>
        <select className="input" style={{ width: 140 }} value={status} onChange={(e) => { setStatus(e.target.value); setPage(0) }}>
          <option value="">Все статусы</option>
          <option value="open">Открытые</option>
          <option value="answered">Отвечено</option>
          <option value="closed">Закрытые</option>
        </select>
        <select className="input" style={{ width: 140 }} value={category} onChange={(e) => { setCategory(e.target.value); setPage(0) }}>
          <option value="">Все категории</option>
          <option value="bug">🐛 Баг</option>
          <option value="suggestion">💡 Предложение</option>
          <option value="question">❓ Вопрос</option>
          <option value="other">📝 Другое</option>
        </select>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--t-40)' }}>{total} тикетов</span>
        {isLoading && <Spinner />}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ paddingLeft: 16 }}>Пользователь</th>
                <th>Категория</th>
                <th>Сообщение</th>
                <th>Статус</th>
                <th>Создан</th>
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}><td colSpan={5}><div className="skeleton" style={{ height: 10, margin: '9px 16px' }} /></td></tr>
                  ))
                : tickets.map((t) => (
                  <tr key={t.id} onClick={() => setSelected(t)} style={{ cursor: 'pointer' }}>
                    <td style={{ paddingLeft: 16 }}>
                      <div style={{ fontSize: 11, color: 'var(--t-80)' }}>{t.first_name || '—'}</div>
                      {t.username && <div style={{ fontSize: 9, color: 'var(--t-40)' }}>@{t.username}</div>}
                    </td>
                    <td style={{ fontSize: 11 }}>{CAT_EMOJI[t.category] ?? '📝'} {t.category}</td>
                    <td style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 10, color: 'var(--t-60)' }}>{t.message}</td>
                    <td><span style={{ fontSize: 9, color: STATUS_COLOR[t.status] ?? 'var(--t-40)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{t.status}</span></td>
                    <td style={{ fontSize: 9, color: 'var(--t-40)' }}>{timeAgo(t.created_at)}</td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
        {!isLoading && !tickets.length && <EmptyState text="Тикетов нет" />}
      </div>

      <Pagination page={page} total={total} pageSize={PG} onChange={(p) => setPage(p)} />

      <AnimatePresence>
        {selected && (
          <TicketDetail
            ticket={selected}
            onClose={() => setSelected(null)}
            onUpdated={() => { qc.invalidateQueries({ queryKey: ['support'] }); setSelected(null) }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function TicketDetail({ ticket, onClose, onUpdated }: { ticket: SupportTicket; onClose: () => void; onUpdated: () => void }) {
  const [reply, setReply] = useState(ticket.admin_reply ?? '')
  const [closeReason, setCloseReason] = useState('')
  const [hideReason, setHideReason] = useState(false)
  const [saving, setSaving] = useState(false)
  const [closing, setClosing] = useState(false)

  async function sendReply() {
    if (!reply.trim()) return
    setSaving(true)
    try {
      await api.replyTicket(ticket.id, reply.trim())
      toast.ok('Ответ отправлен')
      onUpdated()
    } catch (e) { toast.err(extractError(e)) }
    setSaving(false)
  }

  async function closeTicket() {
    if (!closeReason.trim()) { toast.err('Укажите причину закрытия'); return }
    setClosing(true)
    try {
      await api.closeTicket(ticket.id, closeReason.trim(), hideReason)
      toast.ok('Тикет закрыт')
      onUpdated()
    } catch (e) { toast.err(extractError(e)) }
    setClosing(false)
  }

  return (
    <DetailPanel onClose={onClose}>
      <div className="detail-header">
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, color: 'var(--t-100)' }}>{ticket.first_name || `tg:${ticket.tg_id}`}</div>
          <div style={{ fontSize: 9, color: 'var(--t-40)' }}>{CAT_EMOJI[ticket.category]} {ticket.category} · {ticket.status} · {fmtDateTime(ticket.created_at)}</div>
        </div>
        <button className="btn btn-ghost btn-icon" onClick={onClose}><Icon.close /></button>
      </div>
      <div className="detail-body">
        <div style={{ background: 'var(--ink-20)', border: '1px solid var(--line)', borderRadius: 'var(--rad)', padding: '10px 12px', marginBottom: 16, fontSize: 11, lineHeight: 1.6, color: 'var(--t-80)' }}>
          {ticket.message}
        </div>

        {ticket.admin_reply && (
          <div style={{ background: 'var(--ghost2)', border: '1px solid var(--line2)', borderRadius: 'var(--rad)', padding: '10px 12px', marginBottom: 16, fontSize: 11, lineHeight: 1.6, color: 'var(--t-60)' }}>
            <div style={{ fontSize: 9, color: 'var(--t-40)', marginBottom: 6 }}>Ответ поддержки · {timeAgo(ticket.replied_at)}</div>
            {ticket.admin_reply}
          </div>
        )}

        {ticket.status !== 'closed' && (
          <>
            <div className="input-group" style={{ marginBottom: 8 }}>
              <div className="input-label">Ответ пользователю</div>
              <textarea className="input" value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Введите ответ..." style={{ minHeight: 80 }} />
            </div>
            <button className="btn btn-primary w-full" style={{ marginBottom: 16 }} onClick={sendReply} disabled={saving || !reply.trim()}>
              {saving ? <><Spinner /> Отправка...</> : <><Icon.send /> Отправить</>}
            </button>
            <hr className="divider" />
            <div className="input-group" style={{ marginBottom: 8 }}>
              <div className="input-label">Причина закрытия</div>
              <input className="input" value={closeReason} onChange={(e) => setCloseReason(e.target.value)} placeholder="Проблема решена..." />
            </div>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 11, color: 'var(--t-60)', marginBottom: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={hideReason} onChange={(e) => setHideReason(e.target.checked)} style={{ accentColor: 'var(--t-80)' }} />
              Скрыть причину от пользователя
            </label>
            <button className="btn btn-ghost w-full" onClick={closeTicket} disabled={closing}>
              {closing ? <><Spinner /> Закрытие...</> : '🔒 Закрыть тикет'}
            </button>
          </>
        )}
        {ticket.close_reason && (
          <div style={{ padding: '8px 10px', background: 'var(--ink-20)', borderRadius: 'var(--rad)', border: '1px solid var(--line)', marginTop: 12, fontSize: 10, color: 'var(--t-40)' }}>
            <span style={{ color: 'var(--t-60)' }}>Закрыт: </span>{ticket.close_reason}
          </div>
        )}
      </div>
    </DetailPanel>
  )
}
