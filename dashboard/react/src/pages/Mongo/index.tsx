import { useState } from 'react'
import { api, extractError } from '@/api/client'
import { useUIStore, toast } from '@/store/ui'
import { Spinner, EmptyState, SectionHeader, Pagination } from '@/components/common'
import { Icon } from '@/components/common/Icons'
import type { MongoDocument } from '@/types'

const ALLOWED_COLS = [
  'auth_users', 'auth_activity_log', 'auth_error_logs', 'auth_roles', 'auth_api_keys',
  'support_tickets', 'bot_conversations', 'broadcast_jobs',
  'lessons', 'groups', 'teachers', 'rooms', 'institutes', 'scrape_logs',
]

const PG = 20

export function PanelMongo() {
  const [col, setCol] = useState('auth_users')
  const [filter, setFilter] = useState('')
  const [sortStr, setSortStr] = useState('')
  const [docs, setDocs] = useState<MongoDocument[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [filterErr, setFilterErr] = useState('')

  async function load(p = page) {
    // Validate JSON filter client-side before sending
    if (filter.trim()) {
      try { JSON.parse(filter) } catch (e) { setFilterErr('Неверный JSON'); return }
    }
    setFilterErr('')
    setLoading(true)
    try {
      const params: Record<string, string | number> = { collection: col, skip: p * PG, limit: PG }
      if (filter.trim()) params.filter = filter.trim()
      if (sortStr.trim()) params.sort = sortStr.trim()
      const d = await api.getMongo(params as Parameters<typeof api.getMongo>[0])
      setDocs(d.documents)
      setTotal(d.total)
      setPage(p)
      setExpanded(null)
    } catch (e) { toast.err(extractError(e)) }
    setLoading(false)
  }

  const colKeys = docs[0] ? Object.keys(docs[0]).slice(0, 6) : []

  return (
    <div className="anim-up">
      <SectionHeader title="MongoDB Viewer" />

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="input-group" style={{ flex: '1 1 140px' }}>
            <div className="input-label">Коллекция</div>
            <select className="input" value={col} onChange={(e) => setCol(e.target.value)}>
              {ALLOWED_COLS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="input-group" style={{ flex: '2 1 200px' }}>
            <div className="input-label">Фильтр (JSON)</div>
            <input className="input" placeholder='{"is_blocked": true}' value={filter} onChange={(e) => setFilter(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load(0)} />
            {filterErr && <div style={{ fontSize: 9, color: 'var(--t-40)', marginTop: 2 }}>{filterErr}</div>}
          </div>
          <div className="input-group" style={{ flex: '1 1 140px' }}>
            <div className="input-label">Сортировка (поле:1|-1)</div>
            <input className="input" placeholder="timestamp:-1" value={sortStr} onChange={(e) => setSortStr(e.target.value)} />
          </div>
          <button className="btn btn-primary" onClick={() => load(0)} disabled={loading} style={{ alignSelf: 'flex-end' }}>
            {loading ? <Spinner /> : <Icon.search />}
            <span>Запрос</span>
          </button>
        </div>
      </div>

      {docs.length > 0 ? (
        <>
          <div className="card" style={{ padding: 0, marginBottom: 12 }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {colKeys.map((k) => <th key={k} style={{ paddingLeft: k === colKeys[0] ? 16 : undefined }}>{k}</th>)}
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((doc, i) => (
                    <>
                      <tr key={i} onClick={() => setExpanded(expanded === i ? null : i)} style={{ cursor: 'pointer' }}>
                        {colKeys.map((k, ki) => (
                          <td key={k} style={{ paddingLeft: ki === 0 ? 16 : undefined, fontSize: 10, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {renderValue(doc[k])}
                          </td>
                        ))}
                        <td><Icon.chevD /></td>
                      </tr>
                      {expanded === i && (
                        <tr key={`e${i}`}>
                          <td colSpan={colKeys.length + 1} style={{ paddingLeft: 16, paddingBottom: 12, background: 'var(--ink-20)' }}>
                            <pre style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t-60)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', lineHeight: 1.6 }}>
                              {JSON.stringify(doc, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 9, color: 'var(--t-40)' }}>{total} документов</span>
          </div>
          <Pagination page={page} total={total} pageSize={PG} onChange={(p) => load(p)} />
        </>
      ) : loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner lg /></div>
      ) : (
        <EmptyState icon="⬡" text="Нажмите «Запрос» для загрузки документов" />
      )}
    </div>
  )
}

function renderValue(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'boolean') return v ? 'true' : 'false'
  if (typeof v === 'object') return Array.isArray(v) ? `[${(v as unknown[]).length}]` : '{...}'
  const s = String(v)
  return s.length > 40 ? s.slice(0, 40) + '…' : s
}
