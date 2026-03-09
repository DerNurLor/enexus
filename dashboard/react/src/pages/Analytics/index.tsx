import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, extractError } from '@/api/client'
import { useUIStore } from '@/store/ui'
import { Spinner, EmptyState, SectionHeader, Tabs } from '@/components/common'
import { LineChartWidget, BarChartWidget, HeatmapWidget, HorizBar } from '@/components/charts'
import { numFmt } from '@/utils/helpers'

export function PanelAnalytics() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [days, setDays] = useState(7)
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [tab, setTab] = useState('messages')

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics-full', days, from, to, refreshKey],
    queryFn: () => api.getAnalytics({ days, from_date: from || undefined, to_date: to || undefined }),
    staleTime: 30_000,
    retry: 1,
  })

  const msgChartData = useMemo(() => {
    if (!data) return []
    const byDate: Record<string, number> = {}
    data.daily_messages.forEach((d) => { byDate[d.date] = (byDate[d.date] ?? 0) + d.count })
    return Object.entries(byDate).sort().map(([date, count]) => ({ date: date.slice(5), count }))
  }, [data])

  const errChartData = useMemo(() => {
    if (!data) return []
    return data.daily_errors.map((d) => ({ date: d.date.slice(5), count: d.count }))
  }, [data])

  const heatData = useMemo(() => {
    if (!data) return []
    const max = Math.max(...data.hourly_heatmap.map((h) => h.count), 1)
    return data.hourly_heatmap.map((h) => ({ hour: h.hour, pct: (h.count / max) * 100 }))
  }, [data])

  const newUsersData = useMemo(() => {
    if (!data) return []
    return data.new_users_daily.map((d) => ({ date: d.date.slice(5), count: d.count }))
  }, [data])

  const t = data?.totals

  if (error) return <EmptyState icon="⚠" text={extractError(error)} />

  return (
    <div className="anim-up">
      <SectionHeader title="Аналитика" />

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        {[7, 14, 30, 90].map((d) => (
          <button key={d} className={`btn ${days === d && !from ? 'btn-primary' : 'btn-ghost'}`} onClick={() => { setDays(d); setFrom(''); setTo('') }}>
            {d}д
          </button>
        ))}
        <input className="input" type="date" style={{ width: 130 }} value={from} onChange={(e) => setFrom(e.target.value)} />
        <span style={{ color: 'var(--t-40)', fontSize: 11 }}>—</span>
        <input className="input" type="date" style={{ width: 130 }} value={to} onChange={(e) => setTo(e.target.value)} />
        {isLoading && <Spinner />}
      </div>

      {/* KPI cards */}
      {t && (
        <div className="grid-4" style={{ marginBottom: 20 }}>
          {[
            { label: 'Сообщений', value: t.messages },
            { label: 'Ошибок', value: t.errors },
            { label: '👍 Лайков', value: t.fb_likes },
            { label: '👎 Дизлайков', value: t.fb_dislikes },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <div className="stat-label">{s.label}</div>
              <div className="stat-value">{numFmt(s.value)}</div>
            </div>
          ))}
        </div>
      )}

      <Tabs
        tabs={[
          { id: 'messages', label: 'Сообщения' },
          { id: 'errors', label: 'Ошибки' },
          { id: 'users', label: 'Пользователи' },
          { id: 'intents', label: 'Интенты' },
          { id: 'heatmap', label: 'Активность' },
        ]}
        active={tab} onChange={setTab}
      />

      {tab === 'messages' && (
        <div className="grid-2" style={{ gap: 16 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Сообщения по дням</div></div>
            {msgChartData.length > 0
              ? <LineChartWidget data={msgChartData} lines={[{ key: 'count', color: 'var(--t-60)', label: 'Сообщений' }]} />
              : <EmptyState text="Нет данных" />}
          </div>
          <div className="card">
            <div className="card-header"><div className="card-title">Действия в MiniApp</div></div>
            <div>
              {(data?.miniapp_actions ?? []).slice(0, 10).map((a) => (
                <HorizBar key={a.action} label={a.action} count={a.count} max={data?.miniapp_actions[0]?.count ?? 1} />
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'errors' && (
        <div className="grid-2" style={{ gap: 16 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Ошибки по дням</div></div>
            {errChartData.length > 0
              ? <BarChartWidget data={errChartData} dataKey="count" color="var(--t-40)" />
              : <EmptyState text="Нет данных" />}
          </div>
          <div className="card">
            <div className="card-header"><div className="card-title">Ошибки по интенту</div></div>
            {(data?.error_by_intent ?? []).map((e) => (
              <HorizBar key={e.intent} label={e.intent ?? '—'} count={e.count} max={data?.error_by_intent[0]?.count ?? 1} />
            ))}
          </div>
        </div>
      )}

      {tab === 'users' && (
        <div className="card">
          <div className="card-header"><div className="card-title">Новые пользователи</div></div>
          {newUsersData.length > 0
            ? <BarChartWidget data={newUsersData} dataKey="count" color="var(--t-60)" />
            : <EmptyState text="Нет данных" />}
        </div>
      )}

      {tab === 'intents' && (
        <div className="grid-2" style={{ gap: 16 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Топ интентов бота</div></div>
            {(data?.intent_breakdown ?? []).map((i) => (
              <HorizBar key={i.intent} label={i.intent} count={i.count} max={data?.intent_breakdown[0]?.count ?? 1} />
            ))}
          </div>
          <div className="card">
            <div className="card-header"><div className="card-title">Частые запросы с ошибками</div></div>
            {(data?.top_error_queries ?? []).map((q, idx) => (
              <HorizBar key={idx} label={q.query} count={q.count} max={data?.top_error_queries[0]?.count ?? 1} />
            ))}
          </div>
        </div>
      )}

      {tab === 'heatmap' && (
        <div className="card">
          <div className="card-header"><div className="card-title">Активность по часам UTC</div></div>
          <HeatmapWidget data={heatData} />
        </div>
      )}
    </div>
  )
}
