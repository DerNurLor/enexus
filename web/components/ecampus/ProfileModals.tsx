'use client'
/**
 * ProfileModals.tsx — модальные окна для профиля студента.
 * ZachetkaModal — таблица зачётной книжки
 * StatsModal    — интерактивная статистика с графиками
 */
import { useState, useMemo } from 'react'
import { X, ChevronDown, ChevronUp } from 'lucide-react'

// ── Цвета оценок ─────────────────────────────────────────────────────────────
const GRADE_COLOR: Record<string, { bg: string; text: string }> = {
  'отлично':            { bg: '#a6e3a118', text: '#a6e3a1' },
  'хорошо':             { bg: '#89b4fa18', text: '#89b4fa' },
  'удовлетворительно':  { bg: '#f9e2af18', text: '#f9e2af' },
  'неудовлетворительно':{ bg: '#f38ba818', text: '#f38ba8' },
  'зачтено':            { bg: '#94e2d518', text: '#94e2d5' },
  'не зачтено':         { bg: '#f38ba818', text: '#f38ba8' },
}
function gradeStyle(mark: string) {
  return GRADE_COLOR[mark.toLowerCase()] ?? { bg: '#a6adc818', text: '#a6adc8' }
}

// ── Base modal wrapper ────────────────────────────────────────────────────────
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <>
      {/* Backdrop — только затемнение, без blur */}
      <div className="fixed inset-0 z-50"
        style={{ background: 'rgba(0,0,0,0.7)' }}
        onClick={onClose} />
      {/* Модал */}
      <div className="fixed inset-0 z-50 flex items-end lg:items-center justify-center pointer-events-none">
        <div className="pointer-events-auto w-full lg:max-w-2xl max-h-[92vh] flex flex-col rounded-t-3xl lg:rounded-2xl overflow-hidden"
          style={{ background: 'var(--card)', border: '1px solid var(--border)', animation: 'slideInUp 0.28s cubic-bezier(0.34,1.56,0.64,1) forwards' }}>
          {/* Handle */}
          <div className="flex justify-center pt-3 pb-1 lg:hidden shrink-0">
            <div className="w-10 h-1 rounded-full" style={{ background: 'var(--border)' }} />
          </div>
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 shrink-0"
            style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-base font-bold" style={{ color: 'var(--t-primary)' }}>{title}</h2>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors">
              <X size={16} style={{ color: 'var(--t-muted)' }} />
            </button>
          </div>
          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// ЗАЧЁТНАЯ КНИЖКА
// ═══════════════════════════════════════════════════════════════════════════════

interface ZachetkaEntry {
  discipline: string
  mark:       string
  date:       string
  teacher:    string
  type:       string
  hours?:     number
}

interface ZachetkaYear {
  name:    string
  terms:   Array<{ name: string; exams: ZachetkaEntry[]; zachets: ZachetkaEntry[]; other: ZachetkaEntry[] }>
}

interface ZachetkaDetail {
  full_name:    string
  specialty_name?: string
  study_years:  ZachetkaYear[]
}

export function ZachetkaModal({ data, onClose }: { data: any; onClose: () => void }) {
  const [openYear, setOpenYear] = useState<string | null>(null)

  const details: ZachetkaDetail[] = data?.zachetka?.education_details ?? []
  const ovz: any[] = data?.zachetka?.ovz ?? []

  // Флатируем все записи в один поиск
  const [search, setSearch] = useState('')
  const allEntries = useMemo(() => {
    const rows: Array<ZachetkaEntry & { year: string; term: string; course: string }> = []
    for (const detail of details) {
      for (const year of detail.study_years ?? []) {
        for (const term of year.terms ?? []) {
          for (const cat of ['exams', 'zachets', 'other'] as const) {
            for (const entry of (term as any)[cat] ?? []) {
              if (entry.discipline || entry.mark) {
                rows.push({ ...entry, year: year.name, term: term.name, course: detail.full_name })
              }
            }
          }
        }
      }
    }
    return rows
  }, [details])

  const filtered = search.length > 1
    ? allEntries.filter(r => r.discipline?.toLowerCase().includes(search.toLowerCase()))
    : null

  // Авто-открываем последний год
  const allYears = useMemo(() => details.flatMap(d => d.study_years ?? []), [details])
  const displayYear = openYear ?? allYears[allYears.length - 1]?.name ?? null

  return (
    <Modal title="Зачётная книжка" onClose={onClose}>
      <div className="px-4 py-3 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <input type="text" placeholder="Поиск по предмету..." value={search}
          onChange={e => setSearch(e.target.value)}
          className="input-search text-sm w-full" />
      </div>

      {/* Поиск */}
      {filtered && (
        <div className="px-4 py-3">
          {filtered.length === 0 ? (
            <p className="text-sm text-center py-6" style={{ color: 'var(--t-muted)' }}>Ничего не найдено</p>
          ) : (
            <table className="w-full text-[12px] border-collapse">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Предмет', 'Оценка', 'Дата', 'Преподаватель'].map(h => (
                    <th key={h} className="text-left py-2 pr-3 font-semibold text-[10px] uppercase tracking-wider"
                      style={{ color: 'var(--t-muted)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, i) => {
                  const gs = gradeStyle(r.mark ?? '')
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td className="py-2 pr-3" style={{ color: 'var(--t-primary)', maxWidth: 160, wordBreak: 'break-word' }}>{r.discipline}</td>
                      <td className="py-2 pr-3">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                          style={{ background: gs.bg, color: gs.text }}>{r.mark || '—'}</span>
                      </td>
                      <td className="py-2 pr-3 whitespace-nowrap" style={{ color: 'var(--t-muted)' }}>{r.date || '—'}</td>
                      <td className="py-2 pr-3" style={{ color: 'var(--t-secondary)', maxWidth: 140 }}>{r.teacher || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* По годам */}
      {!filtered && (
        <div className="py-2">
          {allYears.map(year => {
            const isOpen = openYear ? openYear === year.name : year.name === allYears[allYears.length - 1]?.name
            const allTermEntries = (year.terms ?? []).flatMap(term =>
              [...(term.exams ?? []), ...(term.zachets ?? []), ...(term.other ?? [])]
            )
            return (
              <div key={year.name}>
                <button onClick={() => setOpenYear(isOpen ? '' : year.name)}
                  className="w-full flex items-center justify-between px-5 py-3 hover:bg-white/3 transition-colors"
                  style={{ borderBottom: '1px solid var(--border)' }}>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>{year.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full"
                      style={{ background: 'var(--surface)', color: 'var(--t-muted)' }}>
                      {allTermEntries.length} записей
                    </span>
                  </div>
                  {isOpen ? <ChevronUp size={14} style={{ color: 'var(--t-muted)' }} />
                          : <ChevronDown size={14} style={{ color: 'var(--t-muted)' }} />}
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 expand-down">
                    {(year.terms ?? []).map(term => {
                      const entries = [...(term.exams ?? []), ...(term.zachets ?? []), ...(term.other ?? [])]
                      if (!entries.length) return null
                      return (
                        <div key={term.name} className="mt-3">
                          <p className="text-[10px] font-semibold uppercase tracking-wider mb-2"
                            style={{ color: 'var(--t-muted)' }}>{term.name}</p>
                          <div className="overflow-x-auto">
                            <table className="w-full text-[12px] border-collapse" style={{ minWidth: 480 }}>
                              <thead>
                                <tr>
                                  {['Предмет', 'Оценка', 'Дата', 'Преподаватель', 'Тип'].map(h => (
                                    <th key={h} className="text-left py-1.5 pr-3 font-semibold text-[10px] uppercase tracking-wider"
                                      style={{ color: 'var(--t-muted)', borderBottom: '1px solid var(--border)' }}>{h}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {entries.map((e, i) => {
                                  const gs = gradeStyle(e.mark ?? '')
                                  return (
                                    <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                                      <td className="py-2 pr-3" style={{ color: 'var(--t-primary)' }}>{e.discipline || '—'}</td>
                                      <td className="py-2 pr-3">
                                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                                          style={{ background: gs.bg, color: gs.text }}>{e.mark || '—'}</span>
                                      </td>
                                      <td className="py-2 pr-3 whitespace-nowrap text-[11px]" style={{ color: 'var(--t-muted)' }}>{e.date || '—'}</td>
                                      <td className="py-2 pr-3 text-[11px]" style={{ color: 'var(--t-secondary)', maxWidth: 140 }}>{e.teacher || '—'}</td>
                                      <td className="py-2 pr-3 text-[10px]" style={{ color: 'var(--t-muted)' }}>{e.type || '—'}</td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}

          {/* ОВЗ / курсовые */}
          {ovz.length > 0 && (
            <div className="px-4 pt-3 pb-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--t-muted)' }}>
                Курсовые работы
              </p>
              {ovz.map((o, i) => {
                const gs = gradeStyle(o.mark ?? '')
                return (
                  <div key={i} className="flex items-center justify-between py-2"
                    style={{ borderBottom: i < ovz.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <div className="min-w-0 mr-3">
                      <p className="text-[12px] font-medium truncate" style={{ color: 'var(--t-primary)' }}>{o.name}</p>
                      <p className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
                        {o.kurs} курс · {o.sem} сем · {o.teacher}
                      </p>
                    </div>
                    <span className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded"
                      style={{ background: gs.bg, color: gs.text }}>{o.mark || '—'}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// СТАТИСТИКА
// ═══════════════════════════════════════════════════════════════════════════════

function DonutChart({ data, title, size = 120 }: {
  data: Array<{ label: string; value: number; color: string }>
  title: string
  size?: number
}) {
  const [hovered, setHovered] = useState<number | null>(null)
  const total = data.reduce((s, d) => s + d.value, 0)
  if (total === 0) return null

  const cx = size / 2, cy = size / 2, r = size * 0.35, strokeW = size * 0.18
  let offset = 0
  const circ = 2 * Math.PI * r

  return (
    <div className="flex flex-col items-center">
      <p className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-center"
        style={{ color: 'var(--t-muted)' }}>{title}</p>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size}>
          {data.map((d, i) => {
            const pct   = d.value / total
            const dash  = pct * circ
            const gap   = circ - dash
            const rot   = offset * 360 - 90
            offset     += pct
            const isHov = hovered === i
            return (
              <circle key={i} cx={cx} cy={cy} r={r}
                fill="none"
                stroke={d.color}
                strokeWidth={isHov ? strokeW + 4 : strokeW}
                strokeDasharray={`${dash} ${gap}`}
                strokeDashoffset={0}
                transform={`rotate(${rot} ${cx} ${cy})`}
                style={{ transition: 'stroke-width 0.2s', cursor: 'pointer', opacity: isHov ? 1 : 0.85 }}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                onTouchStart={() => setHovered(i)}
              />
            )
          })}
        </svg>
        {/* Центр */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          {hovered !== null ? (
            <>
              <span className="text-base font-bold leading-none" style={{ color: data[hovered].color }}>
                {data[hovered].value}
              </span>
              <span className="text-[9px] text-center" style={{ color: 'var(--t-muted)', maxWidth: 50, lineHeight: 1.2 }}>
                {data[hovered].label}
              </span>
            </>
          ) : (
            <>
              <span className="text-base font-bold" style={{ color: 'var(--t-primary)' }}>{total}</span>
              <span className="text-[9px]" style={{ color: 'var(--t-muted)' }}>всего</span>
            </>
          )}
        </div>
      </div>
      {/* Легенда */}
      <div className="flex flex-col gap-1 mt-2 w-full">
        {data.map((d, i) => (
          <div key={i} className="flex items-center justify-between text-[11px]"
            onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ background: d.color, flexShrink: 0 }} />
              <span style={{ color: hovered === i ? 'var(--t-primary)' : 'var(--t-secondary)' }}>{d.label}</span>
            </div>
            <span className="font-mono font-semibold" style={{ color: d.color }}>{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function BarChart({ data, title }: {
  data: Array<{ label: string; value: number; maxValue: number; color: string }>
  title: string
}) {
  const [hovered, setHovered] = useState<number | null>(null)
  if (!data.length) return null
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider mb-3"
        style={{ color: 'var(--t-muted)' }}>{title}</p>
      <div className="flex flex-col gap-2">
        {data.map((d, i) => {
          const pct = d.maxValue > 0 ? (d.value / d.maxValue) * 100 : 0
          const isHov = hovered === i
          return (
            <div key={i}
              onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}
              onTouchStart={() => setHovered(i)}
              className="cursor-default">
              <div className="flex justify-between text-[11px] mb-1">
                <span style={{ color: isHov ? 'var(--t-primary)' : 'var(--t-secondary)' }}>{d.label}</span>
                <span className="font-mono font-semibold" style={{ color: d.color }}>
                  {d.value} <span style={{ color: 'var(--t-muted)', fontWeight: 400 }}>({pct.toFixed(0)}%)</span>
                </span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                <div className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, background: d.color, opacity: isHov ? 1 : 0.75 }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function TimelineChart({ grades, title }: { grades: any[]; title: string }) {
  const SCORE: Record<string, number> = {
    'отлично': 4, 'хорошо': 3, 'удовлетворительно': 2, 'неудовлетворительно': 1,
    'зачтено': 4, 'не зачтено': 1,
  }
  const COLOR: Record<string, string> = {
    'отлично': '#a6e3a1', 'хорошо': '#89b4fa',
    'удовлетворительно': '#f9e2af', 'неудовлетворительно': '#f38ba8',
    'зачтено': '#94e2d5', 'не зачтено': '#f38ba8',
  }

  const pts = useMemo(() => {
    return grades
      .filter(g => g.date && g.grade)
      .map(g => ({
        date:  new Date(g.date).getTime(),
        score: SCORE[g.grade.toLowerCase()] ?? 2.5,
        color: COLOR[g.grade.toLowerCase()] ?? '#a6adc8',
        label: g.grade,
        subj:  g.course_name ?? '',
      }))
      .sort((a, b) => a.date - b.date)
  }, [grades])

  if (pts.length < 3) return null

  const [tooltip, setTooltip] = useState<number | null>(null)
  const W = 300, H = 90, PAD = 12
  const minD = pts[0].date, maxD = pts[pts.length - 1].date
  const xScale = (d: number) => PAD + ((d - minD) / Math.max(maxD - minD, 1)) * (W - PAD * 2)
  const yScale = (s: number) => H - PAD - ((s - 1) / 3) * (H - PAD * 2)

  // Moving average
  const K = Math.min(5, Math.floor(pts.length / 2))
  const ma = pts.map((_, i) => {
    const slice = pts.slice(Math.max(0, i - K), i + 1)
    return slice.reduce((s, p) => s + p.score, 0) / slice.length
  })

  const linePath = ma.map((s, i) => `${i === 0 ? 'M' : 'L'}${xScale(pts[i].date)},${yScale(s)}`).join(' ')

  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider mb-2"
        style={{ color: 'var(--t-muted)' }}>{title}</p>
      <div className="relative">
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: 'visible' }}>
          {/* Y grid */}
          {[1,2,3,4].map(y => (
            <line key={y} x1={PAD} x2={W - PAD} y1={yScale(y)} y2={yScale(y)}
              stroke="var(--border)" strokeWidth={0.5} />
          ))}
          {/* Trend line */}
          <path d={linePath} fill="none" stroke="#cba6f7" strokeWidth={1.5} strokeLinecap="round" opacity={0.7} />
          {/* Points */}
          {pts.map((pt, i) => (
            <circle key={i} cx={xScale(pt.date)} cy={yScale(pt.score)} r={tooltip === i ? 5 : 3.5}
              fill={pt.color} stroke="var(--card)" strokeWidth={1.5}
              style={{ cursor: 'pointer', transition: 'r 0.15s' }}
              onMouseEnter={() => setTooltip(i)}
              onMouseLeave={() => setTooltip(null)}
              onTouchStart={() => setTooltip(i)}
            />
          ))}
        </svg>
        {/* Y labels */}
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between pointer-events-none"
          style={{ fontSize: 9, color: 'var(--t-muted)', paddingTop: PAD - 4, paddingBottom: PAD - 4 }}>
          {['Отл.','Хор.','Удовл.','Неуд.'].map(l => <span key={l}>{l}</span>)}
        </div>
        {/* Tooltip */}
        {tooltip !== null && (
          <div className="absolute pointer-events-none rounded-xl px-2 py-1.5 text-[10px] shadow-lg z-10"
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              left: Math.min(xScale(pts[tooltip].date), W - 100),
              top: yScale(pts[tooltip].score) - 40,
              color: 'var(--t-primary)',
              minWidth: 100,
            }}>
            <div className="font-semibold" style={{ color: pts[tooltip].color }}>{pts[tooltip].label}</div>
            <div style={{ color: 'var(--t-muted)' }}>{pts[tooltip].subj?.slice(0, 20)}</div>
          </div>
        )}
      </div>
    </div>
  )
}

export function StatsModal({ data, onClose }: { data: any; onClose: () => void }) {
  const courses: any[] = data?.courses ?? []

  const allGrades = useMemo(() => {
    const rows: any[] = []
    for (const course of courses) {
      for (const lessonList of Object.values(course.lessons ?? {}) as any[][]) {
        for (const lesson of lessonList) {
          if (lesson.GradeText?.trim()) {
            rows.push({
              grade:       lesson.GradeText.trim().toLowerCase(),
              date:        lesson.Date ?? null,
              course_name: course.Name ?? '',
              term_id:     course.term_id ?? 0,
              term_name:   course.term_name ?? '',
            })
          }
        }
      }
    }
    return rows
  }, [courses])

  // Данные для donut: оценки
  const gradeDonut = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const g of allGrades) counts[g.grade] = (counts[g.grade] ?? 0) + 1
    const ORDER = ['отлично','хорошо','удовлетворительно','неудовлетворительно','зачтено','не зачтено']
    const COLORS: Record<string, string> = {
      'отлично':'#a6e3a1','хорошо':'#89b4fa','удовлетворительно':'#f9e2af',
      'неудовлетворительно':'#f38ba8','зачтено':'#94e2d5','не зачтено':'#f38ba8',
    }
    return ORDER
      .filter(k => counts[k])
      .map(k => ({ label: k.charAt(0).toUpperCase() + k.slice(1), value: counts[k], color: COLORS[k] }))
  }, [allGrades])

  // Данные для donut: типы занятий
  const typeDonut = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const course of courses) {
      for (const lt of course.LessonTypes ?? []) {
        const n = lt.Name ?? 'Другое'
        counts[n] = (counts[n] ?? 0) + 1
      }
    }
    const COLORS = ['#89b4fa','#a78bfa','#94e2d5','#f9e2af','#f38ba8','#cba6f7']
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([k, v], i) => ({ label: k, value: v, color: COLORS[i] }))
  }, [courses])

  // Рейтинг по семестрам (бар)
  const termRating = useMemo(() => {
    const byTerm: Record<string, { sum: number; max: number; cnt: number; name: string }> = {}
    for (const c of courses) {
      const key  = String(c.term_id ?? 0)
      const name = c.term_name ?? key
      if (!byTerm[key]) byTerm[key] = { sum: 0, max: 0, cnt: 0, name }
      if ((c.MaxRating ?? 0) > 0) {
        byTerm[key].sum += c.CurrentRating ?? 0
        byTerm[key].max += c.MaxRating ?? 0
        byTerm[key].cnt++
      }
    }
    const maxVal = Math.max(...Object.values(byTerm).map(b => b.max), 1)
    return Object.values(byTerm)
      .filter(b => b.max > 0)
      .map(b => {
        const pct = b.sum / b.max
        return {
          label:    b.name,
          value:    Math.round(b.sum),
          maxValue: Math.round(b.max),
          color:    pct >= 0.7 ? '#a6e3a1' : pct >= 0.5 ? '#f9e2af' : '#f38ba8',
        }
      })
  }, [courses])

  const totalCourses  = courses.length
  const totalGrades   = allGrades.length
  const excellent     = allGrades.filter(g => g.grade === 'отлично').length
  const excellentPct  = totalGrades > 0 ? Math.round(excellent / totalGrades * 100) : 0

  return (
    <Modal title="Статистика успеваемости" onClose={onClose}>
      <div className="px-4 py-4 flex flex-col gap-6">

        {/* Мини-дашборд */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Предметов',  value: totalCourses,  color: 'var(--accent)' },
            { label: 'Оценок',     value: totalGrades,   color: '#89b4fa' },
            { label: '% Отличных', value: `${excellentPct}%`, color: '#a6e3a1' },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl px-3 py-3 text-center"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="text-lg font-bold tabular-nums" style={{ color }}>{value}</div>
              <div className="text-[10px] mt-0.5" style={{ color: 'var(--t-muted)' }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Два donut рядом */}
        {(gradeDonut.length > 0 || typeDonut.length > 0) && (
          <div className="grid grid-cols-2 gap-4">
            {gradeDonut.length > 0 && <DonutChart data={gradeDonut} title="Оценки" size={110} />}
            {typeDonut.length > 0  && <DonutChart data={typeDonut}  title="Типы занятий" size={110} />}
          </div>
        )}

        {/* Рейтинг по семестрам */}
        {termRating.length > 0 && (
          <BarChart data={termRating} title="Рейтинг по семестрам" />
        )}

        {/* Динамика оценок */}
        {allGrades.length >= 5 && (
          <TimelineChart grades={allGrades} title="Динамика успеваемости" />
        )}

        {/* Топ предметов по оценке */}
        {gradeDonut.length > 0 && (() => {
          const coursesWithRating = courses
            .filter(c => (c.MaxRating ?? 0) > 0)
            .map(c => ({ name: c.Name, pct: (c.CurrentRating ?? 0) / c.MaxRating * 100 }))
            .sort((a, b) => b.pct - a.pct)
            .slice(0, 5)
          if (!coursesWithRating.length) return null
          return (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider mb-2"
                style={{ color: 'var(--t-muted)' }}>Лучшие предметы по рейтингу</p>
              {coursesWithRating.map((c, i) => (
                <div key={i} className="flex items-center justify-between text-[12px] py-1.5"
                  style={{ borderBottom: i < 4 ? '1px solid var(--border)' : 'none' }}>
                  <span className="truncate" style={{ color: 'var(--t-primary)', maxWidth: '70%' }}>{c.name}</span>
                  <span className="font-mono font-semibold ml-2 shrink-0"
                    style={{ color: c.pct >= 70 ? '#a6e3a1' : c.pct >= 50 ? '#f9e2af' : '#f38ba8' }}>
                    {c.pct.toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )
        })()}

      </div>
    </Modal>
  )
}
