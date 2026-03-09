import {
  LineChart as ReLineChart, Line, BarChart as ReBarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

// ── Shared tooltip style ───────────────────────────────────────────────────

const tooltipStyle = {
  background: 'var(--ink-30)',
  border: '1px solid var(--line2)',
  borderRadius: 4,
  fontFamily: 'var(--mono)',
  fontSize: 10,
  color: 'var(--t-80)',
  padding: '6px 10px',
}

// ── Line Chart ─────────────────────────────────────────────────────────────

export function LineChartWidget({ data, lines }: {
  data: Record<string, unknown>[]
  lines: { key: string; color?: string; label?: string }[]
}) {
  return (
    <ResponsiveContainer width="100%" height={120}>
      <ReLineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="date" tick={{ fill: 'var(--t-40)', fontSize: 9, fontFamily: 'var(--mono)' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: 'var(--t-40)', fontSize: 9, fontFamily: 'var(--mono)' }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--t-60)' }} cursor={{ stroke: 'var(--line3)' }} />
        {lines.map((l) => (
          <Line key={l.key} type="monotone" dataKey={l.key} stroke={l.color ?? 'var(--t-80)'} strokeWidth={1.5} dot={false} name={l.label ?? l.key} />
        ))}
      </ReLineChart>
    </ResponsiveContainer>
  )
}

// ── Bar Chart ──────────────────────────────────────────────────────────────

export function BarChartWidget({ data, dataKey, color }: {
  data: Record<string, unknown>[]
  dataKey: string
  color?: string
}) {
  return (
    <ResponsiveContainer width="100%" height={100}>
      <ReBarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="date" tick={{ fill: 'var(--t-40)', fontSize: 9, fontFamily: 'var(--mono)' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: 'var(--t-40)', fontSize: 9, fontFamily: 'var(--mono)' }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--t-60)' }} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
        <Bar dataKey={dataKey} fill={color ?? 'var(--t-20)'} radius={[2, 2, 0, 0]} />
      </ReBarChart>
    </ResponsiveContainer>
  )
}

// ── Heatmap (hourly activity) ──────────────────────────────────────────────

export function HeatmapWidget({ data }: { data: { hour: number; pct: number }[] }) {
  const cells = Array.from({ length: 24 }, (_, i) => data.find((d) => d.hour === i) ?? { hour: i, pct: 0 })
  return (
    <div>
      <div className="heatmap">
        {cells.map(({ hour, pct }) => (
          <div key={hour} className="heatmap-cell" title={`${hour}:00 — ${Math.round(pct)}%`}
            style={{ background: pct > 0 ? `rgba(255,255,255,${0.04 + pct * 0.14})` : 'var(--ink-40)' }} />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        {[0, 6, 12, 18, 23].map((h) => (
          <span key={h} style={{ fontSize: 8, color: 'var(--t-20)', fontFamily: 'var(--mono)' }}>{h}:00</span>
        ))}
      </div>
    </div>
  )
}

// ── Horizontal bar (breakdown) ─────────────────────────────────────────────

export function HorizBar({ label, count, max, color }: { label: string; count: number; max: number; color?: string }) {
  const pct = Math.round((count / Math.max(max, 1)) * 100)
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: 10, color: 'var(--t-60)', fontFamily: 'var(--mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '70%' }}>{label}</span>
        <span style={{ fontSize: 9, color: 'var(--t-40)', fontFamily: 'var(--mono)', flexShrink: 0 }}>{count}</span>
      </div>
      <div style={{ height: 3, background: 'var(--ink-40)', borderRadius: 99 }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color ?? 'var(--t-20)', borderRadius: 99, transition: 'width 0.6s ease', transformOrigin: 'left' }} />
      </div>
    </div>
  )
}
