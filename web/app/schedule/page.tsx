'use client'

import { useState, useRef, useEffect, useCallback, Suspense, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Search, CalendarRange, X, WifiOff, Clock, MapPin, ChevronRight, Star, RefreshCw, History } from 'lucide-react'
import { format, addDays, startOfWeek, getISOWeek } from 'date-fns'
import { ru } from 'date-fns/locale'
import { PageHeader } from '@/components/layout/PageHeader'
import { PillTabs } from '@/components/ui/PillTabs'
import { DayPicker } from '@/components/schedule/DayPicker'
import { LessonCard } from '@/components/schedule/LessonCard'
import { SearchDropdown } from '@/components/schedule/SearchDropdown'
import { useScheduleStore } from '@/lib/store'
import { getToken } from '@/lib/auth'
import { TeacherDashboard } from '@/components/schedule/TeacherDashboard'
import { useGestures }       from '@/hooks/useGestures'
import { api } from '@/lib/api'
import type { Lesson, GroupMeta, TeacherMeta, RoomMeta } from '@/lib/types'
import { useT } from '@/lib/i18n'

type SearchMode = 'group' | 'teacher' | 'room'

function mapLessonType(t: string | null): 'lab' | 'lecture' | 'seminar' | 'practice' | 'exam' | 'credit' | 'consultation' {
  const s = (t || '').toLowerCase()
  if (s.includes('лаб'))              return 'lab'
  if (s.includes('лекц'))             return 'lecture'
  if (s.includes('семин'))            return 'seminar'
  if (s.includes('экзамен'))          return 'exam'
  if (s.includes('зачёт') || s.includes('зачет') || s.includes('диф')) return 'credit'
  if (s.includes('консульт'))         return 'consultation'
  return 'practice'
}

// ── Cache helpers (week-granular) с LRU-эвикцией ─────────────────────────────

const CACHE_PREFIX   = 'schedule_cache:'
const MAX_CACHE_KEYS = 150  // УЛУЧШЕНИЕ: ограничение числа записей в localStorage

function _pruneCache() {
  try {
    const keys = Object.keys(localStorage)
      .filter(k => k.startsWith(CACHE_PREFIX))
      .map(k => {
        try {
          const raw = localStorage.getItem(k)
          const ts = raw ? (JSON.parse(raw) as { saved?: number }).saved ?? 0 : 0
          return { key: k, ts }
        } catch {
          return { key: k, ts: 0 }
        }
      })
      .sort((a, b) => a.ts - b.ts)  // старые первыми

    while (keys.length > MAX_CACHE_KEYS) {
      const oldest = keys.shift()
      if (oldest) localStorage.removeItem(oldest.key)
    }
  } catch { /* localStorage может быть недоступен */ }
}

function weekCacheKey(mode: string, id: number | null, weekNum: number, year: number) {
  return `${CACHE_PREFIX}week:${mode}:${id}:${year}-W${weekNum}`
}

function dayCacheKey(mode: string, id: number | null, date: string) {
  return `${CACHE_PREFIX}day:${mode}:${id}:${date}`
}

function saveWeekToCache(mode: string, id: number | null, weekNum: number, year: number, dayMap: Record<string, Lesson[]>) {
  try {
    const key = weekCacheKey(mode, id, weekNum, year)
    localStorage.setItem(key, JSON.stringify({ saved: Date.now(), days: dayMap }))
    Object.entries(dayMap).forEach(([date, lessons]) => {
      localStorage.setItem(dayCacheKey(mode, id, date), JSON.stringify({ saved: Date.now(), lessons }))
    })
    _pruneCache()  // УЛУЧШЕНИЕ: чистим после каждой записи
  } catch { /* QuotaExceededError — игнорируем */ }
}

function loadDayFromCache(mode: string, id: number | null, date: string): Lesson[] | null {
  try {
    const raw = localStorage.getItem(dayCacheKey(mode, id, date))
    if (!raw) return null
    const parsed = JSON.parse(raw)
    // Поддержка обоих форматов: старый (массив) и новый (объект с saved)
    return Array.isArray(parsed) ? parsed : (parsed.lessons ?? null)
  } catch { return null }
}

// ── Live clock — всегда показываем московское время (UTC+3) ──────────────────
// new Date() возвращает время браузера. Если браузер в UTC или другом поясе —
// format(now, 'HH:mm') покажет неверное время.
// Решение: форматируем через Intl.DateTimeFormat с явным timeZone.

function getMoscowTime(date: Date) {
  const fmt = new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow',
    hour:     '2-digit',
    minute:   '2-digit',
    second:   '2-digit',
    hour12:   false,
  })
  const parts = Object.fromEntries(fmt.formatToParts(date).map(p => [p.type, p.value]))
  return {
    hhmm:    `${parts.hour}:${parts.minute}`,
    hhmmss:  `${parts.hour}:${parts.minute}:${parts.second}`,
    // Для сравнения с временем занятий (они хранятся как "08:30")
    timeStr: `${parts.hour}:${parts.minute}`,
  }
}

function useLiveClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now
}

// ── Component ─────────────────────────────────────────────────────────────────

function SchedulePageInner() {
  const queryClient = useQueryClient()
  const searchParams = useSearchParams()
  const { t } = useT()
  const {
    mode, groupId, groupName, teacherId, teacherName, roomId, roomName,
    setMode, setGroup, setTeacher, setRoom, profile, profileComplete, authToken,
    favorites, setFavorites,
  } = useScheduleStore()

  const SEARCH_MODES: { value: SearchMode; label: string }[] = [
    { value: 'group',   label: t('schedule.type_group') },
    { value: 'teacher', label: t('schedule.type_teacher') },
    { value: 'room',    label: t('schedule.type_room') },
  ]

  const PLACEHOLDER: Record<SearchMode, string> = {
    group:   t('schedule.placeholder_group'),
    teacher: t('schedule.placeholder_teacher'),
    room:    t('schedule.placeholder_room'),
  }

  const isFavorite = useMemo(() => {
    if (mode === 'group' && groupId)
      return favorites.some(f => f.type === 'group' && String(f.id) === String(groupId))
    if (mode === 'teacher' && teacherId)
      return favorites.some(f => f.type === 'teacher' && String(f.id) === String(teacherId))
    return false
  }, [favorites, mode, groupId, teacherId])

  async function toggleFavorite() {
    const token = getToken()
    if (!token) return
    const base = (process.env.NEXT_PUBLIC_API_URL || '') + '/miniapp'
    if (mode === 'group' && groupId && groupName) {
      const fid = `group:${groupId}`
      if (isFavorite) {
        await fetch(`${base}/api/favorites/${encodeURIComponent(fid)}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
        setFavorites(favorites.filter(f => !(f.type === 'group' && String(f.id) === String(groupId))))
      } else {
        await fetch(`${base}/api/favorites`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ type: 'group', id: groupId, label: groupName }) })
        setFavorites([...favorites, { type: 'group', id: groupId, name: groupName }])
      }
      if ('vibrate' in navigator) navigator.vibrate(15)
    } else if (mode === 'teacher' && teacherId && teacherName) {
      const fid = `teacher:${teacherId}`
      if (isFavorite) {
        await fetch(`${base}/api/favorites/${encodeURIComponent(fid)}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
        setFavorites(favorites.filter(f => !(f.type === 'teacher' && String(f.id) === String(teacherId))))
      } else {
        await fetch(`${base}/api/favorites`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ type: 'teacher', id: teacherId, label: teacherName }) })
        setFavorites([...favorites, { type: 'teacher', id: teacherId, name: teacherName }])
      }
      if ('vibrate' in navigator) navigator.vibrate(15)
    }
  }

  function addToHistory(name: string) {
    if (!name) return
    setSearchHistory(prev => {
      const next = [name, ...prev.filter(h => h !== name)].slice(0, 8)
      try { localStorage.setItem('schedule_search_history', JSON.stringify(next)) } catch {}
      return next
    })
  }

  // Загружаем оценки из eCampus если пользователь авторизован и смотрит свою группу
  const isOwnGroup = !!(profile?.groupId && groupId && profile.groupId === groupId)
  const { data: ecampusData } = useQuery({
    queryKey: ['ecampus-data-schedule', authToken],
    queryFn: async () => {
      const { getToken } = await import('@/lib/auth')
      const token = getToken()
      if (!token) return null
      const base = (process.env.NEXT_PUBLIC_API_URL || '') + '/api/ecampus'
      const res = await fetch(`${base}/data`, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) return null
      return res.json()
    },
    enabled: !!authToken && isOwnGroup,
    staleTime: 300_000,
  })

  const gradesIndex = useMemo(() => {
    if (!ecampusData?.courses) return {}
    const index: Record<string, string> = {}
    for (const course of ecampusData.courses) {
      const lessons = course.lessons || {}
      for (const lessonList of Object.values(lessons) as any[][]) {
        for (const lesson of lessonList) {
          if (lesson.GradeText && lesson.Date) {
            const dateKey = lesson.Date.split('T')[0]
            const key = `${course.Name?.toLowerCase().slice(0, 15)}_${dateKey}`
            index[key] = lesson.GradeText
          }
        }
      }
    }
    return index
  }, [ecampusData])

  const [query, setQuery]               = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedDate, setSelectedDateRaw] = useState(new Date())
  function setSelectedDate(next: Date) {
    const prev = selectedDate
    const dir = next > prev ? 'left' : 'right'
    setSlideDir(dir)
    setSelectedDateRaw(next)
    setTimeout(() => setSlideDir(null), 250)
    if ('vibrate' in navigator) navigator.vibrate(6)
  }
  const [isOffline, setIsOffline]       = useState(false)
  const inputRef      = useRef<HTMLInputElement>(null)
  const containerRef  = useRef<HTMLDivElement>(null)
  const [slideDir,     setSlideDir]         = useState<'left' | 'right' | null>(null)
  const [isRefreshing, setIsRefreshing]     = useState(false)
  const [searchHistory, setSearchHistory]   = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('schedule_search_history') || '[]') } catch { return [] }
  })
  const now = useLiveClock()

  // УЛУЧШЕНИЕ: применяем профиль сразу при монтировании если entityId пуст.
  // Без этого пользователь видел «пустой экран» даже когда профиль настроен —
  // store.persist восстанавливает profile, но mode/groupId — отдельные поля,
  // которые при HMR или hard refresh могут быть не восстановлены.
  const profileAppliedRef = useRef(false)
  useEffect(() => {
    if (profileAppliedRef.current) return
    const currentEntityId = mode === 'group' ? groupId : mode === 'teacher' ? teacherId : roomId
    if (!currentEntityId && profileComplete && profile) {
      profileAppliedRef.current = true
      if (profile.role === 'student' && profile.groupId && profile.groupName) {
        setMode('group')
        setGroup(profile.groupId, profile.groupName)
      } else if (profile.role === 'teacher' && profile.teacherId && profile.teacherName) {
        setMode('teacher')
        setTeacher(profile.teacherId, profile.teacherName)
      }
    }
  }, [profile, profileComplete, groupId, teacherId, roomId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Применяем URL-параметры ?mode=&id=&name= при навигации
  useEffect(() => {
    const urlMode = searchParams.get('mode') as 'group' | 'teacher' | 'room' | null
    const urlId   = searchParams.get('id')
    const urlName = searchParams.get('name')
    const urlDate = searchParams.get('date')
    if (urlDate) {
      const parsed = new Date(urlDate)
      if (!isNaN(parsed.getTime())) setSelectedDate(parsed)
    }
    if (urlMode && urlId && urlName) {
      const id = parseInt(urlId, 10)
      if (!isNaN(id)) {
        profileAppliedRef.current = true  // URL-параметры имеют приоритет
        setMode(urlMode)
        if (urlMode === 'group')   setGroup(id, decodeURIComponent(urlName))
        if (urlMode === 'teacher') setTeacher(id, decodeURIComponent(urlName))
        if (urlMode === 'room')    setRoom(id, decodeURIComponent(urlName))
      }
    }
  }, [searchParams]) // eslint-disable-line react-hooks/exhaustive-deps

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

  // Week prefetch
  const prefetchedRef = useRef<Set<string>>(new Set())

  const prefetchWeek = useCallback(async (weekOffset: number) => {
    if (!entityId) return
    const monday = startOfWeek(addDays(new Date(), weekOffset * 7), { weekStartsOn: 1 })
    const weekNum = getISOWeek(monday)
    const year = monday.getFullYear()
    const cKey = weekCacheKey(mode, entityId, weekNum, year)

    if (prefetchedRef.current.has(cKey)) return
    try { if (localStorage.getItem(cKey)) { prefetchedRef.current.add(cKey); return } } catch {}

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
      prefetchedRef.current.delete(cKey)
    }
  }, [entityId, mode])

  const lastPrefetchEntity = useRef<string | null>(null)
  useEffect(() => {
    if (!entityId) return
    const key = `${mode}:${entityId}`
    if (lastPrefetchEntity.current === key) return
    lastPrefetchEntity.current = key
    const t0 = setTimeout(() => prefetchWeek(0), 3000)
    const t1 = setTimeout(() => prefetchWeek(1), 8000)
    return () => { clearTimeout(t0); clearTimeout(t1) }
  }, [entityId, mode]) // eslint-disable-line react-hooks/exhaustive-deps

  // Day query
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

  useEffect(() => {
    if (dayData?.lessons?.length) {
      try { localStorage.setItem(dKey, JSON.stringify({ saved: Date.now(), lessons: dayData.lessons })) } catch {}
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

  const nowStr        = getMoscowTime(now).timeStr
  const isToday       = format(selectedDate, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')
  const currentLesson = isToday ? lessons.find(l => l.time_start <= nowStr && l.time_end >= nowStr) : null
  const nextLesson    = isToday ? lessons.find(l => l.time_start > nowStr) : null

  function handleModeChange(m: SearchMode) {
    setMode(m)
    setQuery('')
    setShowDropdown(false)
  }

  function renderLessons(items: Lesson[]) {
    return (
      <div className="flex flex-col gap-3 stagger-spring">
        {items.map((lesson, i) => {
          const isCurrent = isToday && lesson.time_start <= nowStr && lesson.time_end >= nowStr
          const isPast    = isToday && lesson.time_end < nowStr

          const teacherDisplay = mode === 'teacher' ? null : (lesson.teacher_name || '—')
          const roomDisplay    = mode === 'room'    ? null : (lesson.classroom || lesson.room_name || '—')
          const showGroup      = mode === 'teacher' || mode === 'room'

          return (
            <div key={`${lesson.time_start}-${lesson.subject}-${i}`}
              style={{ opacity: isPast ? 0.5 : 1, transition: 'opacity 0.3s' }}
            >
              {isCurrent && (
                <div className="flex items-center gap-1.5 mb-1 ml-1">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-[10px] font-semibold" style={{ color: '#4ade80' }}>{t('schedule.live_now')}</span>
                </div>
              )}
              <LessonCard lesson={{
                id:          `${dateStr}-${i}`,
                subject:     lesson.subject,
                type:        mapLessonType(lesson.lesson_type),
                teacher:     teacherDisplay || '',
                teacherId:   mode !== 'teacher' ? lesson.teacher_id : null,
                showTeacher: mode !== 'teacher',
                room:        roomDisplay || '',
                roomId:      mode !== 'room' ? (lesson.room_id ?? undefined) : undefined,
                showRoom:    mode !== 'room',
                groupName:   showGroup ? (lesson.group_name || null) : null,
                groupNames:  showGroup ? (lesson.group_names || null) : null,
                groups:      showGroup ? (lesson.groups || null) : null,
                groupId:     showGroup ? (lesson.group_id || null) : null,
                timeStart:   lesson.time_start,
                timeEnd:     lesson.time_end,
                subgroup:    lesson.subgroup ?? undefined,
                note:        lesson.note ?? undefined,
                grade:       isOwnGroup ? (() => {
                  const subjectKey = lesson.subject?.toLowerCase().slice(0, 15) || ''
                  return gradesIndex[`${subjectKey}_${dateStr}`] || null
                })() : null,
              }} />
            </div>
          )
        })}
      </div>
    )
  }

  // Жесты для всей страницы расписания
  const pageGestures = useGestures({
    // Свайп влево — следующий день
    onSwipeLeft: () => setSelectedDate(new Date(selectedDate.getTime() + 86400000)),
    // Свайп вправо — предыдущий день
    onSwipeRight: () => setSelectedDate(new Date(selectedDate.getTime() - 86400000)),
    // Свайп вверх — перейти на сегодня (если не текущая дата)
    onSwipeUp: () => {
      const today = format(new Date(), 'yyyy-MM-dd')
      if (dateStr !== today) setSelectedDate(new Date())
    },
    // Edge swipe слева — предыдущий режим поиска
    onEdgeSwipeRight: () => {
      const modes: SearchMode[] = ['group', 'teacher', 'room']
      const idx = modes.indexOf(mode)
      if (idx > 0) handleModeChange(modes[idx - 1])
    },
    swipeThreshold: 60,
    velocityThreshold: 0.25,
  })

  async function handleRefresh() {
    if (!entityId || isFetching || isRefreshing) return
    if ('vibrate' in navigator) navigator.vibrate(15)
    setIsRefreshing(true)
    await queryClient.invalidateQueries({ queryKey: ['schedule', 'day', mode, entityId, dateStr] })
    setTimeout(() => setIsRefreshing(false), 800)
  }

  return (
    <div className="px-4 lg:px-0" ref={containerRef}
      {...pageGestures}>
      <PageHeader
        title={t('schedule.title')}
        action={
          <div className="flex items-center gap-2">
            {entityId && (
              <button onClick={handleRefresh} disabled={isFetching || isRefreshing}
                className="p-1.5 rounded-lg hover:bg-white/5 transition-all disabled:opacity-40 tap-scale"
                title={t('schedule.refresh_tooltip')}
                style={{ color: isRefreshing ? 'var(--cyan)' : 'var(--t-muted)' }}>
                <RefreshCw size={14} className={isRefreshing || isFetching ? 'animate-spin' : ''} />
              </button>
            )}
            {entityId && authToken && (
              <button onClick={toggleFavorite}
                className="p-1.5 rounded-lg hover:bg-white/5 transition-colors"
                title={isFavorite ? t('schedule.fav_remove_tooltip') : t('schedule.fav_add_tooltip')}
                style={{ color: 'var(--cyan)' }}>
                <Star size={14} fill={isFavorite ? 'var(--cyan)' : 'none'}
                  className={isFavorite ? 'star-bounce' : ''} />
              </button>
            )}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-mono"
              style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--cyan)' }}>
              <Clock size={12} />
              {getMoscowTime(now).hhmmss}
            </div>
          </div>
        }
      />

      {/* Offline banner */}
      {isOffline && (
        <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-xl text-xs"
          style={{ background: 'rgba(255,180,0,0.08)', border: '1px solid rgba(255,180,0,0.2)', color: 'rgba(255,180,0,0.9)' }}>
          <WifiOff size={13} />
          <span>{t('schedule.offline_banner')}</span>
        </div>
      )}

      {/* УЛУЧШЕНИЕ: Виджет «текущая пара» — сразу виден без скролла */}
      {isToday && entityId && currentLesson && (
        <div className="mb-4 px-4 py-3 rounded-xl float"
          style={{ background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.2)' }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-green-400 live-ring flex-shrink-0" style={{ flexShrink: 0 }} />
            <span className="text-xs font-semibold" style={{ color: '#4ade80' }}>{t('schedule.live_now')}</span>
            <span className="text-xs ml-auto" style={{ color: 'var(--t-muted)' }}>
              {t('schedule.until', { time: currentLesson.time_end })}
            </span>
          </div>
          <p className="text-sm font-semibold truncate" style={{ color: 'var(--t-primary)' }}>
            {currentLesson.subject}
          </p>
          {(currentLesson.classroom || currentLesson.room_name) && (
            <div className="flex items-center gap-1 mt-0.5">
              <MapPin size={10} style={{ color: 'var(--t-muted)' }} />
              <span className="text-xs" style={{ color: 'var(--t-muted)' }}>
                {currentLesson.classroom || currentLesson.room_name}
              </span>
            </div>
          )}
        </div>
      )}

      {/* УЛУЧШЕНИЕ: Виджет «следующая пара» — только если нет текущей */}
      {isToday && entityId && !currentLesson && nextLesson && (
        <div className="mb-4 px-4 py-3 rounded-xl"
          style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs" style={{ color: 'var(--t-muted)' }}>{t('schedule.next_lesson')}</span>
            <span className="text-xs font-mono font-semibold" style={{ color: 'var(--cyan)' }}>
              {t('schedule.at_time', { time: nextLesson.time_start })}
            </span>
          </div>
          <p className="text-sm font-semibold truncate" style={{ color: 'var(--t-primary)' }}>
            {nextLesson.subject}
          </p>
        </div>
      )}

      {mode === 'teacher' && teacherId && (
        <TeacherDashboard
          teacherId={teacherId}
          teacherName={teacherName || ''}
          todayLessons={lessons}
          selectedDate={selectedDate}
        />
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
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
        />
        {(query || entityName) && (
          <button className="absolute right-3 top-1/2 -translate-y-1/2"
            onClick={() => { setQuery(''); setShowDropdown(false) }}>
            <X size={14} style={{ color: 'var(--t-muted)' }} />
          </button>
        )}
        {showDropdown && query.length >= 2 && !!searchData && (
          <SearchDropdown mode={mode} data={searchData as any} query={query}
            onSelect={(name) => addToHistory(name)}
            onClose={() => { setShowDropdown(false); setQuery('') }} />
        )}
        {/* История и избранное — когда фокус без запроса */}
        {showDropdown && query.length < 2 && (favorites.length > 0 || searchHistory.length > 0) && (
          <div className="absolute top-full left-0 right-0 mt-1 z-50 rounded-2xl overflow-hidden shadow-xl"
            style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
            {favorites.filter(f => f.type === mode || (mode === 'room' ? false : f.type === mode)).length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 px-3 pt-2.5 pb-1">
                  <Star size={11} style={{ color: 'var(--cyan)' }} />
                  <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>{t('schedule.favorites_label')}</span>
                </div>
                {favorites.filter(f => f.type === mode).map(fav => (
                  <button key={`${fav.type}:${fav.id}`}
                    onMouseDown={() => {
                      if (fav.type === 'group') { setMode('group'); setGroup(Number(fav.id), fav.name); }
                      else { setMode('teacher'); setTeacher(Number(fav.id), fav.name); }
                      setQuery(''); setShowDropdown(false); addToHistory(fav.name)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/5 transition-colors text-sm"
                    style={{ color: 'var(--t-primary)' }}>
                    <Star size={12} fill="var(--cyan)" style={{ color: 'var(--cyan)', flexShrink: 0 }} />
                    {fav.name}
                  </button>
                ))}
              </div>
            )}
            {searchHistory.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 px-3 pt-2.5 pb-1">
                  <History size={11} style={{ color: 'var(--t-muted)' }} />
                  <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>{t('schedule.recent_label')}</span>
                </div>
                {searchHistory.slice(0, 5).map(h => (
                  <button key={h}
                    onMouseDown={() => { setQuery(h); setShowDropdown(true) }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/5 transition-colors text-sm"
                    style={{ color: 'var(--t-secondary)' }}>
                    <History size={12} style={{ color: 'var(--t-muted)', flexShrink: 0 }} />
                    {h}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mb-5">
        <DayPicker selected={selectedDate} onSelect={setSelectedDate} />
      </div>

      {!entityId ? (
        <div className="flex flex-col items-center py-16 gap-3">
          <Search size={40} style={{ color: 'var(--t-muted)' }} />
          <span className="text-sm text-center" style={{ color: 'var(--t-muted)', whiteSpace: 'pre-line' }}>
            {t('schedule.empty_prompt')}
          </span>
          {/* УЛУЧШЕНИЕ: кнопка настройки профиля всегда видна на пустом экране */}
          <Link href="/profile"
            className="mt-2 flex items-center gap-1.5 text-xs px-4 py-2 rounded-xl transition-colors hover:bg-white/5"
            style={{ color: 'var(--cyan)', border: '1px solid rgba(92,225,230,0.3)' }}>
            {profileComplete ? t('schedule.edit_profile') : t('schedule.setup_profile')}
            <ChevronRight size={12} />
          </Link>
        </div>
      ) : (isLoading || isFetching) && !showingCache ? (
        <div className="flex flex-col gap-3">
          {[1,2,3].map(i => (
            <div key={i} className="card px-4 py-3" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="flex items-center gap-2 mb-2">
                <div className="h-5 w-14 rounded-lg skeleton" />
                <div className="h-5 w-20 rounded-lg skeleton" style={{ animationDelay: '0.1s' }} />
              </div>
              <div className="h-4 w-3/4 rounded-lg skeleton mb-1.5" style={{ animationDelay: '0.15s' }} />
              <div className="h-3 w-1/2 rounded-lg skeleton" style={{ animationDelay: '0.2s', opacity: 0.7 }} />
            </div>
          ))}
        </div>
      ) : lessons.length === 0 ? (
        <div className="flex flex-col items-center py-12 gap-3">
          <CalendarRange size={36} style={{ color: 'var(--t-muted)', opacity: 0.5 }} />
          <p className="text-sm font-medium" style={{ color: 'var(--t-secondary)' }}>
            {isOffline ? t('schedule.no_cache_data') : t('schedule.no_lessons')}
          </p>
          {!isOffline && (
            <p className="text-xs" style={{ color: 'var(--t-muted)' }}>
              {isToday ? t('schedule.weekend_or_break') : t('schedule.no_lessons_day')}
            </p>
          )}
          <div className="flex gap-2 mt-1">
            <button onClick={() => {
              const tomorrow = new Date(selectedDate)
              tomorrow.setDate(tomorrow.getDate() + 1)
              setSelectedDate(tomorrow)
            }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs hover:bg-white/5 transition-colors"
              style={{ border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
              {t('schedule.next_day')}
            </button>
          </div>
        </div>
      ) : (
        <>
          {showingCache && (
            <p className="text-xs mb-3" style={{ color: 'var(--t-muted)' }}>{t('schedule.cached_data')}</p>
          )}
          {!showingCache && isFetching && (
            <p className="text-xs mb-3 flex items-center gap-1.5" style={{ color: 'var(--t-muted)' }}>
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--cyan)' }} />
              {t('schedule.updating')}
            </p>
          )}
          <div className={slideDir === 'left' ? 'slide-in-left' : slideDir === 'right' ? 'slide-in-right' : ''}>
            {renderLessons(lessons)}
          </div>
        </>
      )}
    </div>
  )
}

export default function SchedulePage() {
  return (
    <Suspense fallback={<div className="px-4 lg:px-0 animate-pulse"><div className="h-12 rounded-2xl" style={{ background: 'var(--card)' }} /></div>}>
      <SchedulePageInner />
    </Suspense>
  )
}
