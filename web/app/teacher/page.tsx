'use client'
/**
 * web/app/teacher/page.tsx — Страница преподавателя.
 * Плоский UX без аккордеонов. Секции идут сверху вниз.
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { format, getISOWeek } from 'date-fns'
import {
  MapPin, ChevronRight, Copy, Check,
  BookOpen, Clock, Building2, Share2,
  ExternalLink, Search, Users, BarChart2,
} from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { TeacherDashboard } from '@/components/schedule/TeacherDashboard'
import { useScheduleStore } from '@/lib/store'
import { useGestures } from '@/hooks/useGestures'
import { api } from '@/lib/api'
import type { Lesson } from '@/lib/types'

// ── Утилиты ───────────────────────────────────────────────────────────────────

function parseTime(t: string) {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function ltLabel(t: string | null): string {
  const s = (t || '').toLowerCase()
  if (s.includes('лекц'))  return 'Лекция'
  if (s.includes('лаб'))   return 'Лаб.'
  if (s.includes('практ')) return 'Практика'
  if (s.includes('семин')) return 'Семинар'
  if (s.includes('экзам')) return 'Экзамен'
  if (s.includes('зачёт') || s.includes('зачет')) return 'Зачёт'
  return t || 'Другое'
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] uppercase tracking-wider font-semibold mb-2"
      style={{ color: 'var(--t-muted)' }}>
      {children}
    </p>
  )
}

function Divider() {
  return <div className="h-px my-4" style={{ background: 'var(--border)' }} />
}

// ── Поделиться ────────────────────────────────────────────────────────────────

function ShareRow({ teacherId, teacherName }: { teacherId: number; teacherName: string }) {
  const [copied, setCopied] = useState(false)
  const base = typeof window !== 'undefined' ? window.location.origin : ''
  const url  = `${base}/schedule?mode=teacher&id=${teacherId}&name=${encodeURIComponent(teacherName)}`

  return (
    <div className="flex gap-2">
      <div className="flex-1 px-3 py-2 rounded-xl text-[11px] font-mono truncate"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
        {url}
      </div>
      <button onClick={() => { navigator.clipboard.writeText(url).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }) }}
        className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-semibold transition-all"
        style={{
          background: copied ? 'color-mix(in srgb, var(--accent) 15%, transparent)' : 'var(--surface)',
          border: '1px solid var(--border)',
          color: copied ? 'var(--accent)' : 'var(--t-secondary)',
        }}>
        {copied ? <Check size={12} /> : <Copy size={12} />}
        {copied ? 'Скопировано' : 'Копировать'}
      </button>
    </div>
  )
}

// ── Поиск коллеги ─────────────────────────────────────────────────────────────

function ColleagueRow() {
  const [q, setQ] = useState('')
  const router = useRouter()
  const { data } = useQuery({
    queryKey: ['colleague-search', q],
    queryFn:  () => api.searchTeachers(q),
    enabled:  q.length >= 2,
    staleTime: 30_000,
  })
  return (
    <div>
      <div className="relative mb-2">
        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
          style={{ color: 'var(--t-muted)' }} />
        <input type="text" placeholder="Фамилия коллеги…" value={q}
          onChange={e => setQ(e.target.value)}
          className="input-search w-full pl-8 text-sm" />
      </div>
      {data?.teachers && data.teachers.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          {data.teachers.slice(0, 5).map((t, i) => (
            <button key={t.teacher_id}
              onClick={() => router.push(`/schedule?mode=teacher&id=${t.teacher_id}&name=${encodeURIComponent(t.full_name)}`)}
              className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-white/5 transition-colors"
              style={{ borderBottom: i < Math.min(data.teachers.length, 5) - 1 ? '1px solid var(--border)' : 'none' }}>
              <div>
                <p className="text-[13px] font-medium" style={{ color: 'var(--t-primary)' }}>{t.full_name}</p>
                {t.subjects?.length > 0 && (
                  <p className="text-[11px]" style={{ color: 'var(--t-muted)' }}>{t.subjects.slice(0, 2).join(', ')}</p>
                )}
              </div>
              <ExternalLink size={12} style={{ color: 'var(--t-muted)' }} />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Главная ───────────────────────────────────────────────────────────────────

export default function TeacherPage() {
  const router = useRouter()
  const profile     = useScheduleStore(s => s.profile)
  const storeTeId   = useScheduleStore(s => s.teacherId)
  const storeTeName = useScheduleStore(s => s.teacherName)

  const tId   = profile?.teacherId ?? storeTeId
  const tName = profile?.teacherName ?? storeTeName ?? ''
  const today = format(new Date(), 'yyyy-MM-dd')
  const week  = getISOWeek(new Date())

  const { data: todayData } = useQuery({
    queryKey: ['teacher-today', tId, today],
    queryFn:  () => api.getTeacherDay(tId!, today),
    enabled:  !!tId, staleTime: 5 * 60_000,
  })
  const { data: weekData } = useQuery({
    queryKey: ['teacher-week', tId, week],
    queryFn:  () => api.getTeacherWeek(tId!, week),
    enabled:  !!tId, staleTime: 5 * 60_000,
  })
  const { data: teacher } = useQuery({
    queryKey: ['teacher-profile', tId],
    queryFn:  () => api.getTeacher(tId!),
    enabled:  !!tId, staleTime: 60 * 60_000,
  })
  const { data: stats } = useQuery({
    queryKey: ['teacher-stats', tId],
    queryFn:  () => api.getTeacherStats(tId!),
    enabled:  !!tId, staleTime: 60 * 60_000,
  })
  const { data: todayRooms } = useQuery({
    queryKey: ['teacher-today-rooms', tId, today],
    queryFn:  () => api.getTeacherTodayRooms(tId!),
    enabled:  !!tId, staleTime: 5 * 60_000,
  })

  const todayLessons: Lesson[] = todayData?.lessons ?? []

  // Группы недели
  const weekGroups = useMemo(() => {
    if (!weekData?.days) return []
    const map = new Map<string, { name: string; id: number | null; days: Set<string> }>()
    for (const day of weekData.days) {
      for (const l of day.lessons) {
        if (!l.group_name) continue
        if (!map.has(l.group_name)) map.set(l.group_name, { name: l.group_name, id: l.group_id, days: new Set() })
        map.get(l.group_name)!.days.add(day.date)
      }
    }
    return [...map.values()].sort((a, b) => b.days.size - a.days.size)
  }, [weekData])

  // Пересечения
  const overlaps = useMemo(() => {
    if (!weekData?.days) return []
    const res: Array<{ time: string; groups: string[] }> = []
    for (const day of weekData.days) {
      const byTime = new Map<string, string[]>()
      for (const l of day.lessons) {
        const key = `${l.time_start}–${l.time_end}`
        if (!byTime.has(key)) byTime.set(key, [])
        if (l.group_name && !byTime.get(key)!.includes(l.group_name)) byTime.get(key)!.push(l.group_name)
      }
      for (const [time, groups] of byTime) {
        if (groups.length > 1) res.push({ time, groups })
      }
    }
    return res
  }, [weekData])

  // Окна сегодня
  const gaps = useMemo(() => {
    if (todayLessons.length < 2) return []
    const sorted = [...todayLessons].sort((a, b) => a.time_start.localeCompare(b.time_start))
    const res: Array<{ from: string; to: string; mins: number }> = []
    for (let i = 0; i < sorted.length - 1; i++) {
      const diff = parseTime(sorted[i + 1].time_start) - parseTime(sorted[i].time_end)
      if (diff >= 30) res.push({ from: sorted[i].time_end, to: sorted[i + 1].time_start, mins: diff })
    }
    return res
  }, [todayLessons])

  const nowMins = new Date().getHours() * 60 + new Date().getMinutes()
  const curLesson  = todayLessons.find(l => parseTime(l.time_start) <= nowMins && parseTime(l.time_end) >= nowMins)
  const nextLesson = todayLessons.find(l => parseTime(l.time_start) > nowMins)
  const activePair = curLesson || nextLesson

  // Жесты: свайп вверх = обновить все данные преподавателя
  const teacherGestures = useGestures({
    onSwipeUp: () => {
      if (!tId) return
      window.dispatchEvent(new CustomEvent('teacher:refresh', { detail: { tId } }))
    },
    swipeThreshold: 80,
  })

  if (!tId) {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Мои занятия" />
        <div className="flex flex-col items-center py-20 gap-3 text-center">
          <BookOpen size={40} style={{ color: 'var(--t-muted)', opacity: 0.4 }} />
          <p className="text-sm" style={{ color: 'var(--t-muted)' }}>Настройте профиль преподавателя</p>
          <button onClick={() => router.push('/profile')}
            className="flex items-center gap-1.5 text-xs px-4 py-2 rounded-xl"
            style={{ color: 'var(--accent)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}>
            Профиль <ChevronRight size={12} />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 lg:px-0 pb-8 page-enter" {...teacherGestures}>
      <PageHeader title="Мои занятия" />

      {/* ── Текущая / ближайшая пара ──────────────────────────────────── */}
      {activePair && (
        <div className="mb-3 px-4 py-3 rounded-2xl"
          style={{
            background: curLesson ? 'color-mix(in srgb, #4ade80 8%, transparent)' : 'var(--card)',
            border: `1px solid ${curLesson ? 'rgba(74,222,128,0.25)' : 'var(--border)'}`,
          }}>
          <div className="flex items-center justify-between mb-1">
            {curLesson
              ? <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" /><span className="text-[11px] font-semibold" style={{ color: '#4ade80' }}>Сейчас идёт</span></div>
              : <span className="text-[11px]" style={{ color: 'var(--t-muted)' }}>Следующая пара</span>
            }
            <span className="text-[11px] font-mono" style={{ color: 'var(--accent)' }}>
              {activePair.time_start}–{activePair.time_end}
            </span>
          </div>
          <p className="text-sm font-semibold truncate" style={{ color: 'var(--t-primary)' }}>{activePair.subject}</p>
          <div className="flex items-center gap-3 mt-1 text-[11px]" style={{ color: 'var(--t-muted)' }}>
            {activePair.classroom && <span className="flex items-center gap-1"><MapPin size={10} />{activePair.classroom}</span>}
            {activePair.group_name && <span className="flex items-center gap-1"><Users size={10} />{activePair.group_name}</span>}
          </div>
        </div>
      )}

      {/* ── Нагрузка ──────────────────────────────────────────────────── */}
      <TeacherDashboard teacherId={tId} teacherName={tName} todayLessons={todayLessons} selectedDate={new Date()} />

      {/* ── Основной блок ─────────────────────────────────────────────── */}
      <div className="card px-4 py-4">

        {/* Группы недели */}
        {weekGroups.length > 0 && (
          <>
            <SectionTitle>Мои группы на неделе ({weekGroups.length})</SectionTitle>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {weekGroups.map(g => (
                <button key={g.name}
                  onClick={() => router.push(`/schedule?mode=group&id=${g.id ?? ''}&name=${encodeURIComponent(g.name)}`)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[12px] hover:opacity-80 transition-opacity"
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <Users size={11} style={{ color: 'var(--accent)' }} />
                  <span style={{ color: 'var(--t-primary)' }}>{g.name}</span>
                  <span style={{ color: 'var(--t-muted)' }}>{g.days.size}д</span>
                </button>
              ))}
            </div>

            {overlaps.length > 0 && (
              <div className="mb-3">
                {overlaps.slice(0, 3).map((o, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] mb-1">
                    <span className="font-mono" style={{ color: 'var(--t-muted)' }}>{o.time}</span>
                    <span style={{ color: 'var(--t-secondary)' }}>{o.groups.join(', ')}</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px]"
                      style={{ background: 'color-mix(in srgb, #f9e2af 12%, transparent)', color: '#f9e2af' }}>
                      пересечение
                    </span>
                  </div>
                ))}
              </div>
            )}

            {teacher?.group_names && teacher.group_names.length > weekGroups.length && (
              <details className="mb-3">
                <summary className="text-[11px] cursor-pointer" style={{ color: 'var(--t-muted)' }}>
                  Все группы за всё время ({teacher.group_names.length})
                </summary>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {teacher.group_names.map((g, i) => (
                    <button key={i}
                      onClick={() => { const id = teacher.group_ids?.[i]; if (id) router.push(`/schedule?mode=group&id=${id}&name=${encodeURIComponent(g)}`) }}
                      className="px-2.5 py-1 rounded-lg text-[11px] hover:opacity-80"
                      style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
                      {g}
                    </button>
                  ))}
                </div>
              </details>
            )}
            <Divider />
          </>
        )}

        {/* Аудитории сегодня */}
        {todayRooms && todayRooms.rooms.length > 0 && (
          <>
            <SectionTitle>Аудитории сегодня</SectionTitle>
            <div className="flex flex-col gap-1.5 mb-3">
              {todayRooms.rooms.map((r, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2 rounded-xl"
                  style={{ background: 'var(--surface)' }}>
                  <div className="flex items-center gap-2">
                    <Building2 size={13} style={{ color: 'var(--accent)' }} />
                    <div>
                      <span className="text-[13px] font-semibold" style={{ color: 'var(--t-primary)' }}>{r.room_name}</span>
                      {r.building && <span className="text-[11px] ml-2" style={{ color: 'var(--t-muted)' }}>{r.building}</span>}
                    </div>
                  </div>
                  <span className="text-[11px] font-mono" style={{ color: 'var(--t-muted)' }}>{r.time_start}</span>
                </div>
              ))}

              {/* Переходы */}
              {todayRooms.rooms.length > 1 && (() => {
                const tr: Array<{ from: string; to: string; diff: boolean }> = []
                for (let i = 0; i < todayRooms.rooms.length - 1; i++) {
                  const a = todayRooms.rooms[i], b = todayRooms.rooms[i + 1]
                  if (a.room_name !== b.room_name) tr.push({ from: a.room_name, to: b.room_name, diff: a.building !== b.building })
                }
                if (!tr.length) return null
                return (
                  <div className="mt-1 flex flex-col gap-1">
                    {tr.map((t, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-[11px] pl-1">
                        <span style={{ color: 'var(--t-secondary)' }}>{t.from}</span>
                        <ChevronRight size={10} style={{ color: 'var(--t-muted)' }} />
                        <span style={{ color: 'var(--t-secondary)' }}>{t.to}</span>
                        {t.diff && <span className="px-1.5 py-0.5 rounded text-[10px]"
                          style={{ background: 'color-mix(in srgb, #f9e2af 12%, transparent)', color: '#f9e2af' }}>
                          смена корпуса
                        </span>}
                      </div>
                    ))}
                  </div>
                )
              })()}
            </div>

            <button onClick={() => router.push('/map')}
              className="flex items-center gap-2 text-[12px] px-3 py-2 rounded-xl mb-3 hover:bg-white/5 transition-colors"
              style={{ border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
              <MapPin size={12} style={{ color: 'var(--accent)' }} />
              Свободные аудитории рядом
              <ExternalLink size={11} className="ml-auto" style={{ color: 'var(--t-muted)' }} />
            </button>
            <Divider />
          </>
        )}

        {/* Окна сегодня */}
        {gaps.length > 0 && (
          <>
            <SectionTitle>Окна сегодня</SectionTitle>
            <div className="flex flex-wrap gap-2 mb-3">
              {gaps.map((g, i) => (
                <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px]"
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <Clock size={11} style={{ color: 'var(--accent)' }} />
                  <span className="font-mono" style={{ color: 'var(--t-primary)' }}>{g.from}–{g.to}</span>
                  <span style={{ color: 'var(--t-muted)' }}>
                    {Math.floor(g.mins/60)>0?`${Math.floor(g.mins/60)}ч `:''}{g.mins%60>0?`${g.mins%60}м`:''}
                  </span>
                </div>
              ))}
            </div>
            <Divider />
          </>
        )}

        {/* Статистика */}
        {stats && (
          <>
            <SectionTitle>Статистика за всё время</SectionTitle>
            {stats.lesson_types.length > 0 && (
              <div className="mb-3">
                {stats.lesson_types.map(lt => {
                  const pct = Math.round(lt.count / stats.total_lessons * 100)
                  return (
                    <div key={lt.name} className="mb-1.5">
                      <div className="flex justify-between text-[11px] mb-0.5">
                        <span style={{ color: 'var(--t-secondary)' }}>{ltLabel(lt.name)}</span>
                        <span className="font-mono" style={{ color: 'var(--t-muted)' }}>{lt.count} ({pct}%)</span>
                      </div>
                      <div className="h-1 rounded-full" style={{ background: 'var(--border)' }}>
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: 'var(--accent)' }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {stats.top_buildings.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {stats.top_buildings.slice(0, 5).map((b, i) => (
                  <div key={i} className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px]"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    <Building2 size={10} style={{ color: 'var(--accent)' }} />
                    <span style={{ color: 'var(--t-secondary)' }}>{b.name}</span>
                    <span className="font-mono" style={{ color: 'var(--t-muted)' }}>{b.count}</span>
                  </div>
                ))}
              </div>
            )}

            {stats.subjects.length > 0 && (
              <div className="mb-3">
                {stats.subjects.slice(0, 6).map((s, i) => (
                  <div key={i} className="flex justify-between text-[12px] py-1.5"
                    style={{ borderBottom: i < 5 ? '1px solid var(--border)' : 'none' }}>
                    <span className="truncate" style={{ color: 'var(--t-primary)', maxWidth: '75%' }}>{s.name}</span>
                    <span className="font-mono shrink-0 ml-2" style={{ color: 'var(--t-muted)' }}>{s.count}</span>
                  </div>
                ))}
              </div>
            )}
            <Divider />
          </>
        )}

        {/* Поделиться + экспорт */}
        <SectionTitle>Поделиться расписанием</SectionTitle>
        <ShareRow teacherId={tId} teacherName={tName} />

        <button
          onClick={() => { const url = (process.env.NEXT_PUBLIC_API_URL||'')+`/api/schedules/teacher/${tId}/export.ics?weeks=8`; const a=document.createElement('a');a.href=url;a.download=`${tName}.ics`;a.click() }}
          className="flex items-center gap-2 mt-2 px-3 py-2.5 rounded-xl text-[12px] w-full hover:opacity-80 transition-opacity"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
          <Share2 size={13} style={{ color: 'var(--accent)' }} />
          Скачать .ics (8 недель) — Google / Apple / Outlook
        </button>

        <Divider />

        {/* Поиск коллеги */}
        <SectionTitle>Расписание коллеги</SectionTitle>
        <ColleagueRow />

      </div>
    </div>
  )
}
