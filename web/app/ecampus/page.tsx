'use client'
import { useState, useEffect, useMemo, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useScheduleStore } from '@/lib/store'
import { PageHeader } from '@/components/layout/PageHeader'
import {
  BookOpen, RefreshCw, Search, X, ChevronDown, ChevronRight,
  Calendar, MapPin, BarChart2, FileText, AlertCircle, Loader2,
  Star, TrendingUp, Filter, ExternalLink, CheckCircle, Clock,
  GraduationCap, Award, BookMarked, ChevronUp
} from 'lucide-react'

// ── Constants ─────────────────────────────────────────────────────────────────
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/api/ecampus'

const LESSON_TYPE_COLORS: Record<number, string> = {
  1: '#60a5fa', 3: '#34d399', 4: '#f87171', 5: '#fbbf24',
  6: '#a78bfa', 12: '#fb923c', 14: '#94a3b8', 23: '#64748b',
  55: '#f59e0b', 57: '#6366f1',
}
const LESSON_TYPE_NAMES: Record<number, string> = {
  1: 'Лекция', 2: 'Семинар', 3: 'Практика', 4: 'Экзамен', 5: 'Зачёт',
  6: 'Курсовая', 12: 'Контрольная', 14: 'Практ.пр.', 23: 'Сам. работа',
  55: 'Диф. зачёт', 57: 'Предд. пр.', 8: 'Лаборат.',
}
// Типы итоговой аттестации
const EXAM_TYPES = new Set([4]) // только экзамен
const CREDIT_TYPES = new Set([5, 55]) // зачёт и дифф зачёт
const COURSE_WORK_TYPES = new Set([6]) // курсовая
const PRACTICE_TYPES = new Set([14, 57]) // практика
const GRADE_COLORS: Record<string, string> = {
  'отлично': '#34d399', 'хорошо': '#60a5fa',
  'удовлетворительно': '#fbbf24', 'неудовлетворительно': '#f87171',
  'зачтено': '#34d399', 'не зачтено': '#f87171',
}
const TERM_MAP: Record<number, { sem: number; year: number }> = {
  248155: { sem: 1, year: 1 }, 248156: { sem: 2, year: 1 },
  248157: { sem: 3, year: 2 }, 248158: { sem: 4, year: 2 },
  248159: { sem: 5, year: 3 }, 248160: { sem: 6, year: 3 },
  248161: { sem: 7, year: 4 }, 248162: { sem: 8, year: 4 },
}

// ── Helpers ───────────────────────────────────────────────────────────────────
async function authedFetch(path: string, options: RequestInit = {}) {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

async function downloadFile(url: string, label: string) {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  if (!token) { alert('Необходима авторизация'); return }
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) { alert('Ошибка загрузки файла'); return }
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = label
  a.click()
  URL.revokeObjectURL(a.href)
}

function termLabel(tid: number) {
  const t = TERM_MAP[tid]
  return t ? `${t.sem} сем` : `${tid}`
}

// ── Sub-components ────────────────────────────────────────────────────────────
function RatingPill({ value, max }: { value: number; max: number }) {
  if (!max) return null
  const pct = Math.min(value / max * 100, 100)
  const color = pct >= 70 ? '#34d399' : pct >= 40 ? '#fbbf24' : '#f87171'
  return (
    <div className="flex items-center gap-1.5">
      <div className="relative h-1 w-16 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[10px] font-mono tabular-nums" style={{ color }}>
        {value.toFixed(1)}/{max}
      </span>
    </div>
  )
}

function GradeBadge({ grade }: { grade: string }) {
  const color = GRADE_COLORS[grade.toLowerCase()] || '#94a3b8'
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold"
      style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}>
      {grade}
    </span>
  )
}

// ── Course Detail Panel ───────────────────────────────────────────────────────
function CourseDetail({ course, groupId, onClose }: {
  course: any; groupId: number | null; onClose: () => void
}) {
  const [activeTab, setActiveTab] = useState<string | null>(null)
  const router = useRouter()
  const { profile } = useScheduleStore()

  const { data: lessonsData, isLoading: lessonsLoading } = useQuery({
    queryKey: ['ecampus-lessons', course.Id, course.term_id, groupId],
    queryFn: () => authedFetch(`/course/${course.Id}/lessons?term_id=${course.term_id}${groupId ? `&group_id=${groupId}` : ''}`),
    enabled: !!course,
    staleTime: 300_000,
  })

  const { data: materialsData } = useQuery({
    queryKey: ['ecampus-materials', course.Id, course.term_id],
    queryFn: () => authedFetch(`/course/${course.Id}/materials?term_id=${course.term_id}`),
    enabled: !!course,
    staleTime: 600_000,
  })

  useEffect(() => {
    if (lessonsData?.lessons && !activeTab) {
      const firstKey = Object.keys(lessonsData.lessons)[0]
      if (firstKey) setActiveTab(firstKey)
    }
  }, [lessonsData])

  const currentLessons: any[] = (activeTab && lessonsData?.lessons?.[activeTab]) || []
  const gradedLessons = currentLessons.filter((l: any) => l.GradeText?.trim())

  const allGradedCount = useMemo(() => {
    if (!lessonsData?.lessons) return 0
    return Object.values(lessonsData.lessons as Record<string, any[]>)
      .flat().filter((l: any) => l.GradeText?.trim()).length
  }, [lessonsData])

  const lessonTypes = course.LessonTypes || []

  return (
    <div className="flex flex-col gap-3 animate-fade-up">
      {/* Header */}
      <div className="card px-5 py-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-bold leading-snug mb-1" style={{ color: 'var(--t-primary)' }}>
              {course.Name}
            </h2>
            <p className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
              {course.term_name} · {termLabel(course.term_id)}
            </p>
          </div>
          <button onClick={onClose} className="shrink-0 p-1.5 rounded-lg hover:bg-white/5 transition-colors"
            style={{ color: 'var(--t-muted)' }}>
            <X size={14} />
          </button>
        </div>

        {course.MaxRating > 0 && (
          <div className="mb-3">
            <div className="flex justify-between text-[11px] mb-1" style={{ color: 'var(--t-muted)' }}>
              <span>Рейтинг</span>
              <span className="font-mono">{course.CurrentRating?.toFixed(2)} / {course.MaxRating}</span>
            </div>
            <div className="relative h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
              <div className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(course.CurrentRating / course.MaxRating * 100, 100)}%`,
                  background: 'var(--cyan)',
                }} />
            </div>
          </div>
        )}

        {allGradedCount > 0 && (
          <div className="flex items-center gap-1.5 text-[11px]" style={{ color: '#34d399' }}>
            <CheckCircle size={11} />
            <span>{allGradedCount} оценок выставлено</span>
          </div>
        )}

        {/* Типы занятий */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {lessonTypes.map((lt: any) => (
            <span key={lt.Id} className="text-[10px] px-2 py-0.5 rounded-full"
              style={{
                background: `${LESSON_TYPE_COLORS[lt.LessonType] || '#64748b'}15`,
                color: LESSON_TYPE_COLORS[lt.LessonType] || '#64748b',
                border: `1px solid ${LESSON_TYPE_COLORS[lt.LessonType] || '#64748b'}25`,
              }}>
              {LESSON_TYPE_NAMES[lt.LessonType] || lt.Name}
            </span>
          ))}
        </div>
      </div>

      {/* Materials */}
      {materialsData?.materials?.length > 0 && (
        <div className="card px-5 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-2.5"
            style={{ color: 'var(--t-muted)' }}>Материалы</p>
          <div className="flex flex-wrap gap-1.5">
            {materialsData.materials.map((mat: any, i: number) => (
              mat.external ? (
                <a key={i} href={mat.url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] hover:opacity-80 transition-opacity"
                  style={{ background: `${mat.color}15`, color: mat.color, border: `1px solid ${mat.color}25` }}>
                  {mat.icon} {mat.label}
                </a>
              ) : (
                <button key={i} onClick={() => downloadFile(mat.url, mat.label)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] hover:opacity-80 transition-opacity"
                  style={{ background: `${mat.color}15`, color: mat.color, border: `1px solid ${mat.color}25` }}>
                  {mat.icon} {mat.label}
                </button>
              )
            ))}
          </div>
        </div>
      )}

      {/* Lessons & Grades */}
      {lessonsLoading ? (
        <div className="card px-5 py-6 flex items-center justify-center gap-2" style={{ color: 'var(--t-muted)' }}>
          <Loader2 size={14} className="animate-spin" />
          <span className="text-xs">Загрузка занятий...</span>
        </div>
      ) : lessonsData?.lessons && Object.keys(lessonsData.lessons).length > 0 ? (
        <div className="card px-5 py-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 size={13} style={{ color: 'var(--cyan)' }} />
            <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>
              Занятия
            </span>
          </div>

          {/* Type tabs */}
          <div className="flex gap-1 mb-3 overflow-x-auto pb-1">
            {Object.entries(lessonsData.lessons as Record<string, any[]>).map(([typeName, ls]) => {
              const graded = ls.filter((l: any) => l.GradeText?.trim()).length
              return (
                <button key={typeName} onClick={() => setActiveTab(typeName)}
                  className="shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all"
                  style={{
                    background: activeTab === typeName ? 'var(--cyan)' : 'var(--surface)',
                    color: activeTab === typeName ? '#000' : 'var(--t-secondary)',
                    border: `1px solid ${activeTab === typeName ? 'var(--cyan)' : 'var(--border)'}`,
                  }}>
                  {typeName}
                  {graded > 0 && <span className="ml-1 opacity-60">·{graded}</span>}
                </button>
              )
            })}
          </div>

          {/* Lessons list */}
          <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
            {currentLessons.map((lesson: any, i: number) => (
              <div key={lesson.Id || i}
                className="flex items-center gap-2 px-2.5 py-2 rounded-lg group transition-colors hover:bg-white/3"
                style={{ background: 'var(--surface)' }}>
                <span className="shrink-0 text-[10px] font-mono w-14 tabular-nums" style={{ color: 'var(--t-muted)' }}>
                  {lesson.Date ? new Date(lesson.Date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) : '—'}
                </span>
                {lesson.Room && (
                  <span className="shrink-0 text-[10px]" style={{ color: 'var(--t-muted)' }}>
                    {lesson.Room}
                  </span>
                )}
                <div className="flex-1" />
                {lesson.GradeText?.trim() && <GradeBadge grade={lesson.GradeText} />}
                {lesson.GainedScore > 0 && (
                  <span className="shrink-0 text-[10px] font-mono" style={{ color: '#34d399' }}>
                    +{lesson.GainedScore.toFixed(1)}
                  </span>
                )}
                {lesson.Date && groupId && profile?.groupId === groupId && (
                  <button
                    onClick={() => {
                      const date = lesson.Date.split('T')[0]
                      router.push(`/schedule?mode=group&id=${groupId}&name=${encodeURIComponent(profile?.groupName || '')}&date=${date}`)
                    }}
                    className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded"
                    title="Расписание на этот день">
                    <ExternalLink size={10} style={{ color: 'var(--cyan)' }} />
                  </button>
                )}
              </div>
            ))}
            {currentLessons.length === 0 && (
              <p className="text-[11px] text-center py-4" style={{ color: 'var(--t-muted)' }}>
                Нет данных
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function ECampusPage() {
  const { authToken, profile } = useScheduleStore()
  const qc = useQueryClient()

  const [selectedTerm, setSelectedTerm] = useState<number | null>(null)
  const [selectedCourse, setSelectedCourse] = useState<any>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterHasGrades, setFilterHasGrades] = useState(false)
  const [filterHasExam, setFilterHasExam] = useState(false)
  const [filterType, setFilterType] = useState<number | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [sortBy, setSortBy] = useState<'name' | 'rating' | 'grades'>('name')

  const { data: status } = useQuery<any>({
    queryKey: ['ecampus-status', authToken],
    queryFn: () => authedFetch('/status'),
    enabled: !!authToken,
    refetchInterval: 30000,
  })

  const { data: ecampusData, isLoading } = useQuery<any>({
    queryKey: ['ecampus-data', authToken],
    queryFn: () => authedFetch('/data'),
    enabled: !!authToken && status?.connected,
    staleTime: 300_000,
  })

  const syncMutation = useMutation({
    mutationFn: () => authedFetch('/sync', { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ecampus-status'] })
      qc.invalidateQueries({ queryKey: ['ecampus-data'] })
    },
  })

  // Group courses by term
  const coursesByTerm = useMemo(() => {
    if (!ecampusData?.courses) return {} as Record<number, any[]>
    const result: Record<number, any[]> = {}
    for (const c of ecampusData.courses) {
      if (!result[c.term_id]) result[c.term_id] = []
      result[c.term_id].push(c)
    }
    return result
  }, [ecampusData?.courses])

  const termIds = useMemo(() => Object.keys(coursesByTerm).map(Number).sort(), [coursesByTerm])

  // Auto-select last term
  useEffect(() => {
    if (termIds.length && !selectedTerm) {
      setSelectedTerm(termIds[termIds.length - 1])
    }
  }, [termIds])

  // Get all lesson types in current term
  const allLessonTypes = useMemo(() => {
    const courses = selectedTerm ? coursesByTerm[selectedTerm] || [] : []
    const types = new Map<number, string>()
    for (const c of courses) {
      for (const lt of (c.LessonTypes || [])) {
        types.set(lt.LessonType, LESSON_TYPE_NAMES[lt.LessonType] || lt.Name)
      }
    }
    return Array.from(types.entries())
  }, [coursesByTerm, selectedTerm])

  // Filtered + sorted courses
  const filteredCourses = useMemo(() => {
    let courses = selectedTerm ? (coursesByTerm[selectedTerm] || []) : []

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      courses = courses.filter(c => c.Name?.toLowerCase().includes(q))
    }
    if (filterHasGrades) {
      courses = courses.filter(c => {
        const lessons = c.lessons || {}
        return Object.values(lessons as Record<string, any[]>).flat().some((l: any) => l.GradeText?.trim())
      })
    }
    if (filterHasExam) {
      courses = courses.filter(c => c.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType)))
    }
    if (filterType !== null) {
      courses = courses.filter(c => c.LessonTypes?.some((lt: any) => lt.LessonType === filterType))
    }

    // Sort
    if (sortBy === 'rating') {
      courses = [...courses].sort((a, b) => (b.CurrentRating || 0) - (a.CurrentRating || 0))
    } else if (sortBy === 'grades') {
      courses = [...courses].sort((a, b) => {
        const countGrades = (c: any) => Object.values(c.lessons || {}).flat().filter((l: any) => l.GradeText?.trim()).length
        return countGrades(b) - countGrades(a)
      })
    } else {
      courses = [...courses].sort((a, b) => (a.Name || '').localeCompare(b.Name || '', 'ru'))
    }

    return courses
  }, [coursesByTerm, selectedTerm, searchQuery, filterHasGrades, filterHasExam, filterType, sortBy])

  // Term stats
  const termStats = useMemo(() => {
    const courses = selectedTerm ? coursesByTerm[selectedTerm] || [] : []
    const withExam = courses.filter(c => c.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType))).length
    const withCredit = courses.filter(c => c.LessonTypes?.some((lt: any) => CREDIT_TYPES.has(lt.LessonType)) && !c.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType))).length
    const withCourseWork = courses.filter(c => c.LessonTypes?.some((lt: any) => COURSE_WORK_TYPES.has(lt.LessonType))).length
    const withRating = courses.filter(c => c.MaxRating > 0)
    const avgRating = withRating.length
      ? withRating.reduce((s, c) => s + (c.CurrentRating || 0), 0) / withRating.length
      : 0
    const totalGrades = courses.reduce((s, c) =>
      s + Object.values(c.lessons || {}).flat().filter((l: any) => l.GradeText?.trim()).length, 0)
    // Grade distribution
    const allLessons = courses.flatMap(c => Object.values(c.lessons || {}).flat() as any[])
    const gradeDist: Record<string, number> = {}
    for (const l of allLessons) {
      if (l.GradeText?.trim()) {
        const g = l.GradeText.toLowerCase().trim()
        gradeDist[g] = (gradeDist[g] || 0) + 1
      }
    }
    return { total: courses.length, withExam, withCredit, withCourseWork, avgRating, totalGrades, gradeDist }
  }, [coursesByTerm, selectedTerm])

  const isRunning = status?.sync_status === 'running'
  const hasFilters = filterHasGrades || filterHasExam || filterType !== null || searchQuery

  // Not connected
  if (authToken && !isLoading && !status?.connected) {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Предметы" />
        <div className="card px-5 py-10 text-center mt-4">
          <GraduationCap size={36} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm font-semibold mb-1" style={{ color: 'var(--t-primary)' }}>eCampus не подключён</p>
          <p className="text-xs mb-4" style={{ color: 'var(--t-muted)' }}>Подключите eCampus в разделе Профиль</p>
          <a href="/profile" className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-black"
            style={{ background: 'var(--cyan)' }}>Перейти в профиль</a>
        </div>
      </div>
    )
  }

  if (!authToken) {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Предметы" />
        <div className="card px-5 py-10 text-center mt-4">
          <BookOpen size={36} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm font-semibold mb-1" style={{ color: 'var(--t-primary)' }}>Требуется авторизация</p>
          <p className="text-xs" style={{ color: 'var(--t-muted)' }}>Войдите через Telegram в профиле</p>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 lg:px-0 pb-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <PageHeader title="Предметы" />
        <div className="flex items-center gap-2">
          {isRunning && (
            <span className="flex items-center gap-1 text-[11px]" style={{ color: 'var(--cyan)' }}>
              <Loader2 size={11} className="animate-spin" /> Синхронизация
            </span>
          )}
          {status?.last_sync && !isRunning && (
            <span className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
              {new Date(status.last_sync).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}
            </span>
          )}
          <button onClick={() => syncMutation.mutate()}
            disabled={isRunning || syncMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] transition-all hover:bg-white/5 disabled:opacity-40"
            style={{ color: 'var(--cyan)', border: '1px solid var(--cyan)30' }}>
            <RefreshCw size={11} className={isRunning ? 'animate-spin' : ''} />
            Обновить
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[1, 2, 3, 4].map(i => <div key={i} className="card h-16 animate-pulse" />)}
        </div>
      ) : ecampusData ? (
        <div className="flex flex-col gap-4">

          {/* Term selector — grouped by year */}
          {(() => {
            // Group termIds by year
            const byYear: Record<number, number[]> = {}
            for (const tid of termIds) {
              const yr = TERM_MAP[tid]?.year || 0
              if (!byYear[yr]) byYear[yr] = []
              byYear[yr].push(tid)
            }
            const years = Object.keys(byYear).map(Number).sort()
            const selectedYear = selectedTerm ? (TERM_MAP[selectedTerm]?.year || 0) : 0

            return (
              <div className="flex flex-col gap-1.5">
                {/* Year tabs */}
                <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${years.length}, 1fr)` }}>
                  {years.map(yr => {
                    const termsInYear = byYear[yr]
                    const isYearActive = termsInYear.some(tid => tid === selectedTerm)
                    return (
                      <div key={yr}
                        className="card overflow-hidden"
                        style={{ border: `1px solid ${isYearActive ? 'var(--cyan)30' : 'var(--border)'}` }}>
                        {/* Year label */}
                        <div className="px-3 py-1.5 text-center"
                          style={{ borderBottom: '1px solid var(--border)' }}>
                          <span className="text-[10px] font-semibold"
                            style={{ color: isYearActive ? 'var(--cyan)' : 'var(--t-muted)' }}>
                            {yr} курс
                          </span>
                        </div>
                        {/* Semester buttons */}
                        <div className="flex">
                          {termsInYear.map((tid, i) => {
                            const t = TERM_MAP[tid]
                            const count = coursesByTerm[tid]?.length || 0
                            const isActive = selectedTerm === tid
                            return (
                              <button key={tid}
                                onClick={() => { setSelectedTerm(tid); setSelectedCourse(null) }}
                                className="flex-1 py-2 text-center transition-all text-xs"
                                style={{
                                  background: isActive ? 'var(--cyan)' : 'transparent',
                                  color: isActive ? '#000' : 'var(--t-secondary)',
                                  borderLeft: i > 0 ? '1px solid var(--border)' : 'none',
                                  fontWeight: isActive ? 600 : 400,
                                }}>
                                <div className="text-[11px] font-semibold">{t?.sem ?? '?'} сем</div>
                                <div className="text-[9px] opacity-60">{count} пр.</div>
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })()}

          {/* Stats */}
          {selectedTerm && (
            <div className="flex flex-col gap-2">
              {/* Main stats */}
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: 'Всего', value: termStats.total, icon: BookMarked, color: 'var(--cyan)' },
                  { label: 'Оценок', value: termStats.totalGrades, icon: Award, color: '#34d399' },
                  { label: 'Ср. рейтинг', value: termStats.avgRating > 0 ? termStats.avgRating.toFixed(1) : '—', icon: TrendingUp, color: '#fbbf24' },
                  { label: 'Курс. работ', value: termStats.withCourseWork, icon: FileText, color: '#a78bfa' },
                ].map(({ label, value, icon: Icon, color }) => (
                  <div key={label} className="card px-3 py-2.5 text-center">
                    <Icon size={13} className="mx-auto mb-1" style={{ color }} />
                    <div className="text-sm font-bold tabular-nums" style={{ color }}>{value}</div>
                    <div className="text-[9px] mt-0.5" style={{ color: 'var(--t-muted)' }}>{label}</div>
                  </div>
                ))}
              </div>
              {/* Exam/credit breakdown */}
              <div className="card px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider mb-2.5" style={{ color: 'var(--t-muted)' }}>
                  Итоговая аттестация
                </p>
                <div className="flex gap-3 flex-wrap">
                  {[
                    { label: 'Экзаменов', value: termStats.withExam, color: '#f87171' },
                    { label: 'Зачётов', value: termStats.withCredit, color: '#fbbf24' },
                    { label: 'Курс. работ', value: termStats.withCourseWork, color: '#a78bfa' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
                      <span className="text-xs font-semibold tabular-nums" style={{ color }}>{value}</span>
                      <span className="text-xs" style={{ color: 'var(--t-muted)' }}>{label}</span>
                    </div>
                  ))}
                </div>
                {/* Visual bar */}
                {(termStats.withExam + termStats.withCredit + termStats.withCourseWork) > 0 && (
                  <div className="flex h-1.5 rounded-full overflow-hidden mt-2.5 gap-px" style={{ background: 'var(--border)' }}>
                    {termStats.withExam > 0 && (
                      <div className="h-full" style={{ width: `${termStats.withExam / termStats.total * 100}%`, background: '#f87171' }} />
                    )}
                    {termStats.withCredit > 0 && (
                      <div className="h-full" style={{ width: `${termStats.withCredit / termStats.total * 100}%`, background: '#fbbf24' }} />
                    )}
                    {termStats.withCourseWork > 0 && (
                      <div className="h-full" style={{ width: `${termStats.withCourseWork / termStats.total * 100}%`, background: '#a78bfa' }} />
                    )}
                  </div>
                )}
              </div>
              {/* Grade distribution */}
              {termStats.totalGrades > 0 && Object.keys(termStats.gradeDist).length > 0 && (
                <div className="card px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider mb-2.5" style={{ color: 'var(--t-muted)' }}>
                    Распределение оценок
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {Object.entries(termStats.gradeDist)
                      .sort((a, b) => b[1] - a[1])
                      .map(([grade, count]) => {
                        const color = GRADE_COLORS[grade] || '#94a3b8'
                        const pct = count / termStats.totalGrades * 100
                        return (
                          <div key={grade} className="flex items-center gap-2">
                            <span className="text-[11px] w-28 truncate capitalize" style={{ color }}>{grade}</span>
                            <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                              <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
                            </div>
                            <span className="text-[10px] font-mono tabular-nums w-6 text-right" style={{ color }}>{count}</span>
                          </div>
                        )
                      })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Search + Filters */}
          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                  style={{ color: 'var(--t-muted)' }} />
                <input
                  type="text"
                  placeholder="Поиск предмета..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="input-search w-full pl-9 pr-8 text-sm"
                />
                {searchQuery && (
                  <button onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2">
                    <X size={12} style={{ color: 'var(--t-muted)' }} />
                  </button>
                )}
              </div>
              <button
                onClick={() => setShowFilters(v => !v)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-all"
                style={{
                  background: (showFilters || hasFilters) ? 'var(--cyan-dim)' : 'var(--card)',
                  color: (showFilters || hasFilters) ? 'var(--cyan)' : 'var(--t-secondary)',
                  border: `1px solid ${(showFilters || hasFilters) ? 'var(--cyan)' : 'var(--border)'}`,
                }}>
                <Filter size={12} />
                Фильтры
                {hasFilters && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
              </button>
            </div>

            {showFilters && (
              <div className="card px-4 py-3 flex flex-col gap-3 animate-fade-up">
                {/* Quick filters */}
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { label: 'Есть оценки', active: filterHasGrades, toggle: () => setFilterHasGrades(v => !v) },
                    { label: 'Экзамен', active: filterHasExam, toggle: () => setFilterHasExam(v => !v) },
                  ].map(({ label, active, toggle }) => (
                    <button key={label} onClick={toggle}
                      className="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all"
                      style={{
                        background: active ? 'var(--cyan)' : 'var(--surface)',
                        color: active ? '#000' : 'var(--t-secondary)',
                        border: `1px solid ${active ? 'var(--cyan)' : 'var(--border)'}`,
                      }}>
                      {label}
                    </button>
                  ))}
                </div>

                {/* Lesson type filter */}
                {allLessonTypes.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    <button onClick={() => setFilterType(null)}
                      className="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all"
                      style={{
                        background: filterType === null ? 'var(--surface)' : 'var(--surface)',
                        color: filterType === null ? 'var(--cyan)' : 'var(--t-muted)',
                        border: `1px solid ${filterType === null ? 'var(--cyan)' : 'var(--border)'}`,
                      }}>
                      Все типы
                    </button>
                    {allLessonTypes.map(([typeId, name]) => (
                      <button key={typeId} onClick={() => setFilterType(filterType === typeId ? null : typeId)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all"
                        style={{
                          background: filterType === typeId ? `${LESSON_TYPE_COLORS[typeId] || '#64748b'}15` : 'var(--surface)',
                          color: filterType === typeId ? (LESSON_TYPE_COLORS[typeId] || '#64748b') : 'var(--t-muted)',
                          border: `1px solid ${filterType === typeId ? (LESSON_TYPE_COLORS[typeId] || '#64748b') + '40' : 'var(--border)'}`,
                        }}>
                        {name}
                      </button>
                    ))}
                  </div>
                )}

                {/* Sort */}
                <div className="flex items-center gap-2">
                  <span className="text-[11px]" style={{ color: 'var(--t-muted)' }}>Сортировка:</span>
                  {[
                    { key: 'name', label: 'По названию' },
                    { key: 'rating', label: 'По рейтингу' },
                    { key: 'grades', label: 'По оценкам' },
                  ].map(({ key, label }) => (
                    <button key={key} onClick={() => setSortBy(key as any)}
                      className="px-2 py-0.5 rounded text-[11px] transition-all"
                      style={{
                        color: sortBy === key ? 'var(--cyan)' : 'var(--t-muted)',
                        fontWeight: sortBy === key ? 600 : 400,
                      }}>
                      {label}
                    </button>
                  ))}
                </div>

                {hasFilters && (
                  <button onClick={() => {
                    setFilterHasGrades(false); setFilterHasExam(false)
                    setFilterType(null); setSearchQuery('')
                  }}
                    className="text-[11px] self-start"
                    style={{ color: '#f87171' }}>
                    Сбросить фильтры
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Course list + detail */}
          <div className="lg:grid lg:grid-cols-2 lg:gap-4">
            {/* List */}
            <div className="flex flex-col gap-1.5">
              {filteredCourses.length === 0 ? (
                <div className="card px-5 py-8 text-center">
                  <Search size={24} className="mx-auto mb-2 opacity-30" />
                  <p className="text-sm" style={{ color: 'var(--t-muted)' }}>Предметы не найдены</p>
                </div>
              ) : filteredCourses.map((course: any) => {
                const isSelected = selectedCourse?.Id === course.Id && selectedCourse?.term_id === course.term_id
                const hasExam = course.LessonTypes?.some((lt: any) => [4, 5, 55].includes(lt.LessonType))
                const gradeCount = Object.values(course.lessons || {}).flat()
                  .filter((l: any) => l.GradeText?.trim()).length

                return (
                  <button key={`${course.Id}-${course.term_id}`}
                    onClick={() => setSelectedCourse(isSelected ? null : course)}
                    className="w-full text-left px-4 py-3 rounded-xl transition-all"
                    style={{
                      background: isSelected ? 'var(--cyan-dim)' : 'var(--card)',
                      border: `1px solid ${isSelected ? 'var(--cyan)' : 'var(--border)'}`,
                    }}>
                    <div className="flex items-start gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-medium leading-snug truncate"
                          style={{ color: isSelected ? 'var(--cyan)' : 'var(--t-primary)' }}>
                          {course.Name}
                        </p>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          {course.LessonTypes?.slice(0, 3).map((lt: any) => (
                            <span key={lt.Id} className="text-[9px] px-1.5 py-0.5 rounded"
                              style={{
                                background: `${LESSON_TYPE_COLORS[lt.LessonType] || '#64748b'}15`,
                                color: LESSON_TYPE_COLORS[lt.LessonType] || '#64748b',
                              }}>
                              {LESSON_TYPE_NAMES[lt.LessonType] || lt.Name}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        {course.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType)) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ background: '#f8717115', color: '#f87171' }}>Экзамен</span>
                        )}
                        {course.LessonTypes?.some((lt: any) => CREDIT_TYPES.has(lt.LessonType)) && !course.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType)) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ background: '#fbbf2415', color: '#fbbf24' }}>
                            {course.LessonTypes?.some((lt: any) => lt.LessonType === 55) ? 'Диф.зачёт' : 'Зачёт'}
                          </span>
                        )}
                        {course.LessonTypes?.some((lt: any) => COURSE_WORK_TYPES.has(lt.LessonType)) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ background: '#a78bfa15', color: '#a78bfa' }}>Курс.р.</span>
                        )}
                        {gradeCount > 0 && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ background: '#34d39915', color: '#34d399' }}>
                            {gradeCount} оц.
                          </span>
                        )}
                        {course.MaxRating > 0 && (
                          <RatingPill value={course.CurrentRating} max={course.MaxRating} />
                        )}
                      </div>
                    </div>
                  </button>
                )
              })}
              <p className="text-center text-[11px] py-2" style={{ color: 'var(--t-muted)' }}>
                {filteredCourses.length} из {coursesByTerm[selectedTerm || 0]?.length || 0} предметов
              </p>
            </div>

            {/* Detail */}
            {selectedCourse && (
              <div className="mt-4 lg:mt-0">
                <CourseDetail
                  course={selectedCourse}
                  groupId={profile?.groupId ?? null}
                  onClose={() => setSelectedCourse(null)}
                />
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="card px-5 py-8 text-center">
          <p className="text-sm" style={{ color: 'var(--t-muted)' }}>
            Нет данных. Нажмите «Обновить» для синхронизации.
          </p>
        </div>
      )}
    </div>
  )
}
