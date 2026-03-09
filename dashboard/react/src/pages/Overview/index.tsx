import { useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, extractError } from '@/api/client'
import { useUIStore } from '@/store/ui'
import { SectionHeader, EmptyState, Spinner } from '@/components/common'
import { LineChartWidget, HorizBar, HeatmapWidget } from '@/components/charts'
import { numFmt, timeAgo } from '@/utils/helpers'

function StatCard({ label, value, delta, barPct }: { label: string; value: number | string; delta?: string; barPct?: number }) {
  return (
    <motion.div className="stat-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{typeof value === 'number' ? numFmt(value) : value}</div>
      {delta && <div className="stat-delta">{delta}</div>}
      {barPct != null && (
        <div className="stat-bar">
          <div className="stat-bar-fill" style={{ width: `${barPct}%` }} />
        </div>
      )}
    </motion.div>
  )
}

export function PanelOverview() {
  const refreshKey = useUIStore((s) => s.refreshKey)

  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['stats', refreshKey],
    queryFn: () => api.getStats(),
    staleTime: 30_000,
    retry: 1,
  })

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analytics', 7, refreshKey],
    queryFn: () => api.getAnalytics({ days: 7 }),
    staleTime: 30_000,
    retry: 1,
  })

  if (statsLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner lg /></div>
  if (statsError) return <EmptyState icon="⚠" text={extractError(statsError)} />

  const t = stats?.totals
  const activity = analytics?.daily_messages ?? []

  // Group messages by date, sum roles
  const msgByDate: Record<string, number> = {}
  activity.forEach((d) => {
    msgByDate[d.date] = (msgByDate[d.date] ?? 0) + d.count
  })
  const msgChartData = Object.entries(msgByDate).sort().map(([date, count]) => ({ date: date.slice(5), count }))

  const heatData = (analytics?.hourly_heatmap ?? []).map((h) => ({
    hour: h.hour,
    pct: (h.count / Math.max(...(analytics?.hourly_heatmap ?? []).map((x) => x.count), 1)) * 100,
  }))

  return (
    <div className="anim-up">
      <SectionHeader title="Обзор" />

      {/* Stats grid */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        <StatCard label="Всего пользователей" value={t?.users ?? 0} barPct={100} />
        <StatCard label="Активны сегодня" value={t?.active_today ?? 0} delta={`из ${t?.users ?? 0}`} barPct={t?.users ? (t.active_today / t.users) * 100 : 0} />
        <StatCard label="Заблокировано" value={t?.blocked ?? 0} />
        <StatCard label="Тикетов открыто" value={t?.open_tickets ?? 0} />
      </div>

      <div className="grid-4" style={{ marginBottom: 20 }}>
        <StatCard label="Занятий в БД" value={t?.total_lessons ?? 0} />
        <StatCard label="Групп" value={t?.total_groups ?? 0} />
        <StatCard label="Преподавателей" value={t?.total_teachers ?? 0} />
        <StatCard label="Вызовов API сегодня" value={t?.api_calls_today ?? 0} />
      </div>

      <div className="grid-2-1" style={{ marginBottom: 20 }}>
        {/* Daily messages chart */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Сообщения (7 дней)</div>
            {analyticsLoading && <Spinner />}
          </div>
          {msgChartData.length > 0
            ? <LineChartWidget data={msgChartData} lines={[{ key: 'count', color: 'var(--t-60)', label: 'Сообщений' }]} />
            : <EmptyState text="Нет данных" />
          }
        </div>

        {/* Top actions */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Топ действий</div>
          </div>
          <div style={{ overflow: 'hidden' }}>
            {(stats?.action_breakdown ?? []).slice(0, 8).map((a, i) => (
              <HorizBar key={a.action} label={a.action} count={a.count} max={stats?.action_breakdown[0]?.count ?? 1} />
            ))}
          </div>
        </div>
      </div>

      {/* Hourly heatmap */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div className="card-title">Активность по часам</div>
        </div>
        <HeatmapWidget data={heatData} />
      </div>

      <div className="grid-2">
        {/* Recent events */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Последние события</div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Действие</th><th>tg_id</th><th>Время</th></tr></thead>
              <tbody>
                {(stats?.recent_events ?? []).map((e, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 10, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.action}</td>
                    <td style={{ fontSize: 10, color: 'var(--t-40)' }}>{e.tg_id ?? '—'}</td>
                    <td style={{ fontSize: 9, color: 'var(--t-40)' }}>{timeAgo(e.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Scrape stats */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Парсинг расписания</div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Режим</th><th>Группы</th><th>Занятия</th><th>Статус</th></tr></thead>
              <tbody>
                {(stats?.scrape_stats?.recent ?? []).map((s, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 10 }}>{s.mode || '—'}</td>
                    <td>{s.groups_scraped}</td>
                    <td>{s.lessons_upserted}</td>
                    <td><span className={`badge ${s.status === 'ok' ? 'badge-neutral' : 'badge-dark'}`}>{s.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
