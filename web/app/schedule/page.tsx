'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, CalendarRange, X, WifiOff, Clock } from 'lucide-react'
import { format, addDays, startOfWeek, getISOWeek } from 'date-fns'
import { ru } from 'date-fns/locale'
import { PageHeader } from '@/components/layout/PageHeader'
import { PillTabs } from '@/components/ui/PillTabs'
import { DayPicker } from '@/components/schedule/DayPicker'
import { LessonCard } from '@/components/schedule/LessonCard'
import { SearchDropdown } from '@/components/schedule/SearchDropdown'
import { useScheduleStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Lesson, GroupMeta, TeacherMeta, RoomMeta } from '@/lib/types'

type SearchMode = 'group' | 'teacher' | 'room'

const SEARCH_MODES: { value: SearchMode; label: string }[] = [
  { value: 'group',   label: 'Группа' },
  { value: 'teacher', label: 'Преподаватель' },
  { value: 'room',    label: 'Аудитория' },
]

const PLACEHOLDER: Record<SearchMode, string> = {
  group:   'напр. ИС-21',
  teacher: 'напр. Иванов И.И.',
  room:    'напр. А-308',
}

function mapLessonType(t: string | null): 'lab' | 'lecture' | 'seminar' | 'practice' {
  const s = (t || '').toLowerCase()
  if (s.includes('лаб'))   return 'lab'
  if (s.includes('лекц'))  return 'lecture'
  if (s.includes('семин')) return 'seminar'
  return 'practice'
}

// ── Cache helpers (week-granular) ─────────────────────────────────────────────

function weekCacheKey(mode: string, id: number | null, weekNum: number, year: number) {
  return `schedule_cache:week:${mode}:${id}:${year}-W${weekNum}`
}

function dayCacheKey(mode: string, id: number | null, date: string) {
  return `schedule_cache:day:${mode}:${id}:${date}`
}

function saveWeekToCache(mode: string, id: number | null, weekNum: number, year: number, dayMap: Record<string, Lesson[]>) {
  try {
    const key = weekCacheKey(mode, id, weekNum, year)
    localStorage.setItem(key, JSON.stringify({ saved: Date.now(), days: dayMap }))
    // Also store individual day entries for fast lookup
    Object.entries(dayMap).forEach(([date, lessons]) => {
      localStorage.setItem(dayCacheKey(mode, id, date), JSON.stringify(lessons))
    })
  } catch {}
}

function loadDayFromCache(mode: string, id: number | null, date: string): Lesson[] | null {
  try {
    const raw = localStorage.getItem(dayCacheKey(mode, id, date))
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

// ── Live clock ────────────────────────────────────────────────────────────────

function useLiveClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function SchedulePage() {
  const queryClient = useQueryClient()
  const { mode, groupId, groupName, teacherId, teacherName, roomId, roomName, setMode, profile, profileComplete } =
    useScheduleStore()
  const [query, setQuery]               = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [isOffline, setIsOffline]       = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const now = useLiveClock()

  const entityId   = mode === 'group' ? groupId   : mode === 'teacher' ? teacherId   : roomId
  const entityName = mode === 'group' ? groupName : mode === 'teacher' ? teacherName : roomName
  const dateStr    = format(selectedDate, 'yyyy-MM-dd')
  const dKey       = dayCacheKey(mode, entityId, dateStr)

  // Track online/offline
  useEffect(() => {
    setIsOffline(!navigator.onLine)
    const on  = () => setIsOffline(false)
    const off = () => setIsOffline(true)
    window.addEventListener('online',  on)
    window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])

  // ── Week prefetch: cache current + next week on load ──────────────────────
  const prefetchedRef = useRef<Set<string>>(new Set())

  const prefetchWeek = useCallback(async (weekOffset: number) => {
    if (!entityId) return
    const monday = startOfWeek(addDays(new Date(), weekOffset * 7), { weekStartsOn: 1 })
    const weekNum = getISOWeek(monday)
    const year = monday.getFullYear()
    const cKey = weekCacheKey(mode, entityId, weekNum, year)

    // Skip if already cached in localStorage or already being fetched this session
    if (prefetchedRef.current.has(cKey)) return
    try {
      if (localStorage.getItem(cKey)) { prefetchedRef.current.add(cKey); return }
    } catch {}

    prefetchedRef.current.add(cKey)
    try {
      let weekData
      if (mode === 'group')        weekData = await api.getGroupWeek(entityId, weekNum)
      else if (mode === 'teacher') weekData = await api.getTeacherWeek(entityId, weekNum)
      else                         weekData = await api.getRoomWeek(entityId, weekNum)

      if (weekData?.days) {
        const dayMap: Record<string, Lesson[]> = {}
        weekData.days.forEach((d: any) => { dayMap[d.date] = d.lessons ?? [] })
        saveWeekToCache(mode, entityId, weekNum, year, dayMap)
      }
    } catch {
      prefetchedRef.current.delete(cKey) // allow retry next time
    }
  }, [entityId, mode])

  useEffect(() => {
    if (!entityId) return
    // Stagger requests to avoid hitting rate limit
    const t0 = setTimeout(() => prefetchWeek(0), 800)
    const t1 = setTimeout(() => prefetchWeek(1), 2500)
    const t2 = setTimeout(() => prefetchWeek(2), 4500)
    return () => { clearTimeout(t0); clearTimeout(t1); clearTimeout(t2) }
  }, [entityId, mode, prefetchWeek])

  // ── Day query ─────────────────────────────────────────────────────────────
  const { data: dayData, isLoading, isFetching, isError } = useQuery({
    queryKey: ['schedule', 'day', mode, entityId, dateStr],
    queryFn:  async () => {
      if (!entityId) return null
      if (mode === 'group')   return api.getGroupDay(entityId, dateStr)
      if (mode === 'teacher') return api.getTeacherDay(entityId, dateStr)
      return api.getRoomDay(entityId, dateStr)
    },
    enabled: !!entityId,
    retry: 1,
    staleTime: 1000 * 60 * 5,
  })

  // Save day to cache
  useEffect(() => {
    if (dayData?.lessons?.length) {
      try { localStorage.setItem(dKey, JSON.stringify(dayData.lessons)) } catch {}
    }
  }, [dayData, dKey])

  // Search query
  const { data: searchData } = useQuery<
    { total: number; groups?: GroupMeta[]; teachers?: TeacherMeta[]; rooms?: RoomMeta[] } | null
  >({
    queryKey: ['search', mode, query],
    queryFn:  () => {
      if (query.length < 2) return null
      if (mode === 'group')   return api.searchGroups(query)
      if (mode === 'teacher') return api.searchTeachers(query)
      return api.searchRooms(query)
    },
    enabled: query.length >= 2,
  })

  const liveLessons: Lesson[]   = dayData?.lessons || []
  const cachedLessons: Lesson[] = loadDayFromCache(mode, entityId, dateStr) || []
  const showingCache = (isOffline || isError) && liveLessons.length === 0 && cachedLessons.length > 0
  const lessons      = showingCache ? cachedLessons : liveLessons

  // Find currently running lesson
  const nowStr = format(now, 'HH:mm')
  const currentLesson = lessons.find(l => l.time_start <= nowStr && l.time_end >= nowStr)
  const isToday = format(selectedDate, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')

  function handleModeChange(m: SearchMode) {
    setMode(m)
    setQuery('')
    setShowDropdown(false)
  }

  function renderLessons(items: Lesson[]) {
    return (
      <div className="flex flex-col gap-3 stagger">
        {items.map((lesson, i) => {
          const isCurrent = isToday && lesson.time_start <= nowStr && lesson.time_end >= nowStr
          const isPast    = isToday && lesson.time_end < nowStr

          // В режиме преподавателя — показываем группу вместо преподавателя
          // В режиме аудитории — показываем преподавателя (группа идёт отдельным полем)
          const teacherDisplay = mode === 'teacher'
            ? null  // не показываем — это сам преподаватель
            : (lesson.teacher_name || '—')

          const roomDisplay = mode === 'room'
            ? null  // не показываем аудиторию — мы уже в её расписании
            : (lesson.classroom || lesson.room_name || '—')

          // group показываем только когда смотрим преподавателя или аудиторию
          const showGroup = mode === 'teacher' || mode === 'room'

          return (
            <div key={i}
              style={{ opacity: isPast ? 0.5 : 1, transition: 'opacity 0.3s' }}
            >
              {isCurrent && (
                <div className="flex items-center gap-1.5 mb-1 ml-1">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-[10px] font-semibold" style={{ color: '#4ade80' }}>Сейчас идёт</span>
                </div>
              )}
              <LessonCard lesson={{
                id:          String(i),
                subject:     lesson.subject,
                type:        mapLessonType(lesson.lesson_type),
                teacher:     teacherDisplay || '',
                teacherId:   mode !== 'teacher' ? lesson.teacher_id : null,
                showTeacher: mode !== 'teacher',
                room:        roomDisplay || '',
                roomId:      mode !== 'room' ? (lesson.room_id ?? undefined) : undefined,
                showRoom:    mode !== 'room',
                groupName:   showGroup ? (lesson.group_name || null) : null,
                groupId:     showGroup ? (lesson.group_id || null) : null,
                timeStart:   lesson.time_start,
                timeEnd:     lesson.time_end,
                subgroup:    lesson.subgroup ?? undefined,
                note:        lesson.note ?? undefined,
              }} />
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="px-4 lg:px-0">
      <PageHeader
        title="Расписание"
        action={
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-mono"
            style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--cyan)' }}>
            <Clock size={12} />
            {format(now, 'HH:mm:ss')}
          </div>
        }
      />

      {/* Offline banner */}
      {isOffline && (
        <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-xl text-xs"
          style={{ background: 'rgba(255,180,0,0.08)', border: '1px solid rgba(255,180,0,0.2)', color: 'rgba(255,180,0,0.9)' }}>
          <WifiOff size={13} />
          <span>Нет подключения — показываем кешированные данные</span>
        </div>
      )}

      <div className="mb-3">
        <PillTabs options={SEARCH_MODES} value={mode} onChange={handleModeChange} />
      </div>

      <div className="relative mb-4">
        <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10"
          style={{ color: 'var(--t-muted)' }} />
        <input ref={inputRef} className="input-search pl-10 pr-10"
          placeholder={entityName || PLACEHOLDER[mode]}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setShowDropdown(true) }}
          onFocus={() => query.length >= 2 && setShowDropdown(true)}
        />
        {(query || entityName) && (
          <button className="absolute right-3 top-1/2 -translate-y-1/2"
            onClick={() => { setQuery(''); setShowDropdown(false) }}>
            <X size={14} style={{ color: 'var(--t-muted)' }} />
          </button>
        )}
        {showDropdown && query.length >= 2 && !!searchData && (
          <SearchDropdown mode={mode} data={searchData as any}
            onClose={() => { setShowDropdown(false); setQuery('') }} />
        )}
      </div>

      <div className="mb-5">
        <DayPicker selected={selectedDate} onSelect={setSelectedDate} />
      </div>

      {!entityId ? (
        <div className="flex flex-col items-center py-16 gap-3">
          <Search size={40} style={{ color: 'var(--t-muted)' }} />
          <span className="text-sm text-center" style={{ color: 'var(--t-muted)' }}>
            Введите название группы,<br />преподавателя или аудитории
          </span>
          {!profileComplete && (
            <a href="/profile"
              className="mt-2 text-xs px-4 py-2 rounded-xl transition-colors hover:bg-white/5"
              style={{ color: 'var(--cyan)', border: '1px solid rgba(92,225,230,0.3)' }}>
              Настроить профиль →
            </a>
          )}
        </div>
      ) : (isLoading || isFetching) && !showingCache ? (
        <div className="flex flex-col gap-3">
          {[1,2,3].map(i => (
            <div key={i} className="card h-20 animate-pulse" style={{ opacity: 0.5 }} />
          ))}
        </div>
      ) : lessons.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3">
          <CalendarRange size={40} style={{ color: 'var(--t-muted)' }} />
          <span className="text-sm" style={{ color: 'var(--t-muted)' }}>
            {isOffline ? 'Нет данных в кеше для этого дня' : (dayData?.message || 'Занятий нет')}
          </span>
        </div>
      ) : (
        <>
          {showingCache && (
            <p className="text-xs mb-3" style={{ color: 'var(--t-muted)' }}>📦 Данные из кеша</p>
          )}
          {!showingCache && isFetching && (
            <p className="text-xs mb-3 flex items-center gap-1.5" style={{ color: 'var(--t-muted)' }}>
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--cyan)' }} />
              Обновление…
            </p>
          )}
          {renderLessons(lessons)}
        </>
      )}
    </div>
  )
}
