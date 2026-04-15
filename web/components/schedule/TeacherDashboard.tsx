'use client'
/**
 * TeacherDashboard — панель нагрузки для преподавателей.
 *
 * Показывается над обычным расписанием когда выбран режим «Преподаватель».
 * Загружает данные текущей недели и строит:
 *   1. Тепловую карту занятости (пн–пт × 8 слотов времени)
 *   2. Дашборд нагрузки: пар/день, часов, групп, типов занятий
 *   3. «Окна» в расписании сегодня
 *   4. Кнопку экспорта .ics
 */

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getISOWeek } from 'date-fns'
import { ChevronDown, ChevronUp, Download, Clock, Layers } from 'lucide-react'
import { api } from '@/lib/api'
import type { Lesson, WeekResponse } from '@/lib/types'

// ── Временные слоты ────────────────────────────────────────────────────────────
const TIME_SLOTS = [
  '08:00', '09:35', '11:10', '12:45', '14:20', '16:00', '17:35', '19:10',
]
const SLOT_LABELS = ['08:00', '09:35', '11:10', '12:45', '14:20', '16:00', '17:35', '19:10']
const DAYS_SHORT  = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт']
const DAY_INDICES: Record<string, number> = {
  'Понедельник': 0, 'Вторник': 1, 'Среда': 2, 'Четверг': 3, 'Пятница': 4,
  'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4,
}

function lessonSlot(timeStart: string): number {
  const [h, m] = timeStart.split(':').map(Number)
  const mins = h * 60 + m
  // Находим ближайший слот
  for (let i = TIME_SLOTS.length - 1; i >= 0; i--) {
    const [sh, sm] = TIME_SLOTS[i].split(':').map(Number)
    if (mins >= sh * 60 + sm - 5) return i
  }
  return 0
}

function lessonDayIndex(weekdayName: string): number {
  return DAY_INDICES[weekdayName] ?? -1
}

// ── Тепловая карта ────────────────────────────────────────────────────────────
function HeatmapCell({ count, max }: { count: number; max: number }) {
  const pct = max > 0 ? count / max : 0
  const bg =
    count === 0  ? 'var(--border)' :
    pct <= 0.33  ? 'color-mix(in srgb, var(--cyan) 30%, transparent)' :
    pct <= 0.66  ? 'color-mix(in srgb, var(--cyan) 60%, transparent)' :
                   'var(--cyan)'
  return (
    <div
      className="rounded-md flex items-center justify-center text-[10px] font-mono font-semibold transition-all"
      style={{
        background: bg,
        color: count === 0 ? 'var(--t-muted)' : pct > 0.5 ? '#000' : 'var(--cyan)',
        aspectRatio: '1',
        minWidth: 28,
        minHeight: 28,
        opacity: count === 0 ? 0.35 : 1,
      }}
    >
      {count > 0 ? count : ''}
    </div>
  )
}

// ── Ближайшие "окна" ──────────────────────────────────────────────────────────
function parseTime(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + (m || 0)
}

function formatMins(mins: number): string {
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return h > 0 ? `${h}ч ${m > 0 ? m + 'м' : ''}`.trim() : `${m}м`
}

interface Gap {
  from: string
  to:   string
  mins: number
}

function findGaps(lessons: Lesson[]): Gap[] {
  if (lessons.length < 2) return []
  const sorted = [...lessons].sort((a, b) => a.time_start.localeCompare(b.time_start))
  const gaps: Gap[] = []
  for (let i = 0; i < sorted.length - 1; i++) {
    const endMin   = parseTime(sorted[i].time_end)
    const startMin = parseTime(sorted[i + 1].time_start)
    const diff     = startMin - endMin
    if (diff >= 30) {
      gaps.push({ from: sorted[i].time_end, to: sorted[i + 1].time_start, mins: diff })
    }
  }
  return gaps
}

// ── ICS export ────────────────────────────────────────────────────────────────
function exportICS(teacherId: number, teacherName: string, week: number) {
  const url = (process.env.NEXT_PUBLIC_API_URL || '') +
    `/api/schedules/teacher/${teacherId}/export.ics?weeks=4`
  const a = document.createElement('a')
  a.href = url
  a.download = `${teacherName.replace(/\s+/g, '_')}_w${week}.ics`
  a.click()
}

// ── Тип занятия → метка ───────────────────────────────────────────────────────
function lessonTypeLabel(t: string | null): string {
  const s = (t || '').toLowerCase()
  if (s.includes('лекц'))                          return 'Лекция'
  if (s.includes('лаб'))                           return 'Лаб.'
  if (s.includes('практ'))                         return 'Практика'
  if (s.includes('семин'))                         return 'Семинар'
  if (s.includes('экзам'))                         return 'Экзамен'
  if (s.includes('зачёт') || s.includes('зачет')) return 'Зачёт'
  if (s.includes('консульт'))                      return 'Консультация'
  return t || 'Другое'
}

// ── Главный компонент ─────────────────────────────────────────────────────────
interface Props {
  teacherId:   number
  teacherName: string
  todayLessons: Lesson[]   // уже загруженные уроки текущего дня
}

export function TeacherDashboard({ teacherId, teacherName, todayLessons }: Props) {
  const [expanded, setExpanded] = useState(false)
  const currentWeek = getISOWeek(new Date())

  const { data: weekData, isLoading } = useQuery<WeekResponse>({
    queryKey: ['teacher-week-dash', teacherId, currentWeek],
    queryFn:  () => api.getTeacherWeek(teacherId, currentWeek),
    staleTime: 5 * 60_000,
  })

  // ── Агрегация данных за неделю ──────────────────────────────────────────────
  const stats = useMemo(() => {
    if (!weekData?.days) return null

    // grid[dayIdx][slotIdx] = количество пар
    const grid: number[][] = Array.from({ length: 5 }, () => Array(TIME_SLOTS.length).fill(0))
    let totalLessons = 0
    let totalMinutes = 0
    const groupSet   = new Set<string>()
    const typeCount: Record<string, number> = {}

    for (const day of weekData.days) {
      // weekday_name может отсутствовать в ответе /teachers/{id}/week —
      // вычисляем день недели из даты (0=вс, 1=пн, ... 6=сб)
      let dayIdx: number
      if (day.weekday_name && DAY_INDICES[day.weekday_name] !== undefined) {
        dayIdx = DAY_INDICES[day.weekday_name]
      } else if (day.date) {
        const jsDay = new Date(day.date + 'T00:00:00').getDay() // 0=вс
        dayIdx = jsDay === 0 ? 6 : jsDay - 1                    // 0=пн..4=пт
      } else {
        continue
      }
      if (dayIdx < 0 || dayIdx > 4) continue

      for (const l of day.lessons) {
        const slotIdx = lessonSlot(l.time_start)
        grid[dayIdx][slotIdx]++
        totalLessons++
        totalMinutes += parseTime(l.time_end) - parseTime(l.time_start)

        if (l.group_name) groupSet.add(l.group_name)
        if (l.group_names) l.group_names.forEach(g => groupSet.add(g))

        const typeKey = lessonTypeLabel(l.lesson_type)
        typeCount[typeKey] = (typeCount[typeKey] || 0) + 1
      }
    }

    const maxCell    = Math.max(...grid.flat())
    const daysWithLessons = weekData.days.filter(d => d.lessons.length > 0).length
    const avgPerDay  = daysWithLessons > 0 ? (totalLessons / daysWithLessons) : 0
    const totalHours = Math.round(totalMinutes / 60 * 10) / 10

    const topTypes = Object.entries(typeCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)

    return { grid, maxCell, totalLessons, totalHours, groupCount: groupSet.size, avgPerDay, topTypes }
  }, [weekData])

  // «Окна» сегодня
  const gaps = useMemo(() => findGaps(todayLessons), [todayLessons])

  if (isLoading) {
    return (
      <div className="mb-4 card px-4 py-3 animate-pulse" style={{ height: 80 }} />
    )
  }

  return (
    <div className="mb-4 rounded-2xl overflow-hidden"
      style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>

      {/* Шапка */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/3 transition-colors"
        onClick={() => setExpanded(v => !v)}
      >
        <div className="flex items-center gap-2">
          <Layers size={14} style={{ color: 'var(--cyan)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>
            Нагрузка на неделю
          </span>
          {stats && (
            <span className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: 'var(--surface)', color: 'var(--t-muted)' }}>
              {stats.totalLessons} пар · {stats.totalHours}ч
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); exportICS(teacherId, teacherName, currentWeek) }}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] hover:bg-white/5 transition-colors"
            style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}
            title="Скачать .ics"
          >
            <Download size={11} />
            .ics
          </button>
          {expanded ? <ChevronUp size={14} style={{ color: 'var(--t-muted)' }} />
                    : <ChevronDown size={14} style={{ color: 'var(--t-muted)' }} />}
        </div>
      </button>

      {expanded && stats && (
        <div className="px-3 pb-3 flex flex-col gap-3">

          {/* ── Компактная строка цифр ─────────────────────────────────── */}
          <div className="flex items-center gap-0 rounded-xl overflow-hidden"
            style={{ background: 'var(--surface)' }}>
            {[
              { label: 'пар/день', value: stats.avgPerDay.toFixed(1) },
              { label: 'часов',    value: stats.totalHours },
              { label: 'групп',    value: stats.groupCount },
              { label: 'всего пар',value: stats.totalLessons },
            ].map(({ label, value }, i, arr) => (
              <div key={label} className="flex-1 flex flex-col items-center py-2"
                style={{ borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}>
                <span className="text-sm font-bold tabular-nums" style={{ color: 'var(--t-primary)' }}>
                  {value}
                </span>
                <span className="text-[9px]" style={{ color: 'var(--t-muted)' }}>{label}</span>
              </div>
            ))}
          </div>

          {/* ── Тепловая карта ──────────────────────────────────────────── */}
          <div className="overflow-x-auto">
            <div style={{ minWidth: 240 }}>
              <div className="grid mb-1" style={{ gridTemplateColumns: '36px repeat(5, 1fr)', gap: 3 }}>
                <div />
                {DAYS_SHORT.map(d => (
                  <div key={d} className="text-center text-[10px] font-semibold"
                    style={{ color: 'var(--t-muted)' }}>{d}</div>
                ))}
              </div>
              {TIME_SLOTS.map((slot, slotIdx) => (
                <div key={slot} className="grid mb-1" style={{ gridTemplateColumns: '36px repeat(5, 1fr)', gap: 3 }}>
                  <div className="flex items-center text-[9px] font-mono"
                    style={{ color: 'var(--t-muted)', lineHeight: 1 }}>
                    {SLOT_LABELS[slotIdx].slice(0, 5)}
                  </div>
                  {Array.from({ length: 5 }, (_, dayIdx) => (
                    <HeatmapCell key={dayIdx} count={stats.grid[dayIdx][slotIdx]} max={stats.maxCell} />
                  ))}
                </div>
              ))}
            </div>
          </div>

          {/* ── Типы + Окна в одну строку ───────────────────────────────── */}
          <div className="flex gap-3">
            {/* Типы занятий */}
            {stats.topTypes.length > 0 && (
              <div className="flex-1 min-w-0">
                <p className="text-[9px] uppercase tracking-wider mb-1.5 font-semibold"
                  style={{ color: 'var(--t-muted)' }}>Типы</p>
                <div className="flex flex-col gap-1">
                  {stats.topTypes.map(([type, cnt]) => {
                    const pct = Math.round(cnt / stats.totalLessons * 100)
                    return (
                      <div key={type} className="flex items-center gap-1.5">
                        <span className="text-[10px] truncate" style={{ color: 'var(--t-secondary)', minWidth: 0, flex: 1 }}>
                          {type}
                        </span>
                        <div className="h-1 rounded-full flex-shrink-0" style={{ width: 40, background: 'var(--border)' }}>
                          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: 'var(--cyan)' }} />
                        </div>
                        <span className="text-[9px] font-mono flex-shrink-0" style={{ color: 'var(--t-muted)' }}>{pct}%</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Окна сегодня */}
            {gaps.length > 0 && (
              <div className="flex-1 min-w-0">
                <p className="text-[9px] uppercase tracking-wider mb-1.5 font-semibold"
                  style={{ color: 'var(--t-muted)' }}>Окна сегодня</p>
                <div className="flex flex-col gap-1">
                  {gaps.map((g, i) => (
                    <div key={i} className="flex items-center gap-1 text-[10px]">
                      <span className="font-mono" style={{ color: 'var(--t-primary)' }}>
                        {g.from}–{g.to}
                      </span>
                      <span style={{ color: 'var(--t-muted)' }}>{formatMins(g.mins)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  )
}
