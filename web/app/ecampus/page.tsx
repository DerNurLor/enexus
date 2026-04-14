'use client'
import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useScheduleStore } from '@/lib/store'
import { PageHeader } from '@/components/layout/PageHeader'
import {
  BookOpen, RefreshCw, Search, X, BarChart2, FileText,
  Loader2, GraduationCap, Award, BookMarked, TrendingUp,
  ExternalLink, CheckCircle, ChevronDown, ChevronUp,
} from 'lucide-react'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/api/ecampus'

const LESSON_TYPE_COLORS: Record<number, string> = {
  1: '#60a5fa', 3: '#34d399', 4: '#f87171', 5: '#fbbf24',
  6: '#a78bfa', 12: '#fb923c', 14: '#94a3b8', 23: '#64748b',
  55: '#f59e0b', 57: '#6366f1', 8: '#4ade80',
}
const LESSON_TYPE_NAMES: Record<number, string> = {
  1: 'Лекция', 2: 'Семинар', 3: 'Практика', 4: 'Экзамен', 5: 'Зачёт',
  6: 'Курсовая', 8: 'Лаб.', 12: 'Контрольная', 14: 'Практ.пр.',
  23: 'Сам. работа', 55: 'Диф. зачёт', 57: 'Предд. пр.',
}
const EXAM_TYPES        = new Set([4])
const CREDIT_TYPES      = new Set([5, 55])
const COURSE_WORK_TYPES = new Set([6])
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
  a.download = label; a.click()
  URL.revokeObjectURL(a.href)
}

// ── Loading spinner ───────────────────────────────────────────────────────────
function CourseSpinner() {
  return (
    <div className="flex items-center justify-center w-7 h-7 shrink-0">
      <svg viewBox="0 0 28 28" width="28" height="28">
        <circle cx="14" cy="14" r="11" fill="none" stroke="var(--border)" strokeWidth="2.5"/>
        <circle cx="14" cy="14" r="11" fill="none" stroke="var(--accent)" strokeWidth="2.5"
          strokeLinecap="round" strokeDasharray="20 50"
          style={{ transformOrigin: '14px 14px', animation: 'spin 0.9s linear infinite' }}/>
      </svg>
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

// ── Sync progress bar ─────────────────────────────────────────────────────────
function SyncProgressBar({ status }: { status: any }) {
  if (status?.sync_status !== 'running') return null
  const progress     = status.sync_progress ?? 0
  const doneTerm     = status.sync_done_terms ?? 0
  const totalTerms   = status.sync_total_terms ?? 0
  const coursesFound = status.sync_courses_found ?? 0
  const stage =
    progress < 5  ? '🔌 Подключение к eCampus...' :
    progress < 20 ? '🔐 Авторизация на портале...' :
    progress < 40 ? '📚 Загрузка списка семестров...' :
    progress < 60 ? (totalTerms > 0 ? `📖 Семестр ${doneTerm} из ${totalTerms} — сбор предметов...` : '📖 Загрузка предметов...') :
    progress < 80 ? '📝 Загрузка оценок и материалов...' :
    progress < 95 ? '💾 Сохранение данных...' :
                    '✅ Почти готово...'

  return (
    <div className="mb-4 px-4 py-3 rounded-xl"
      style={{ background: 'color-mix(in srgb, var(--accent) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--accent) 20%, transparent)' }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--accent)' }}>{stage}</span>
        </div>
        <span className="text-[11px] font-mono font-semibold" style={{ color: 'var(--accent)' }}>{Math.max(5, progress)}%</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden mb-2" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.max(5, progress)}%`, background: 'var(--accent)' }} />
      </div>
      {coursesFound > 0 && (
        <div className="text-[10px]" style={{ color: 'var(--t-muted)' }}>
          Найдено предметов: {coursesFound}
        </div>
      )}
    </div>
  )
}

// ── Bottom sheet (мобайл) ─────────────────────────────────────────────────────
function BottomSheet({ open, onClose, children }: {
  open: boolean; onClose: () => void; children: React.ReactNode
}) {
  const sheetRef = useRef<HTMLDivElement>(null)
  const startY   = useRef(0)
  const isDragging = useRef(false)

  useEffect(() => {
    if (open) document.body.style.overflow = 'hidden'
    else document.body.style.overflow = ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      {/* Backdrop */}
      <div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.5)' }}
        onClick={onClose} />
      {/* Sheet */}
      <div ref={sheetRef}
        className="absolute bottom-0 left-0 right-0 rounded-t-3xl overflow-hidden flex flex-col animate-fade-up"
        style={{ background: 'var(--surface)', maxHeight: '90vh' }}
        onTouchStart={e => { startY.current = e.touches[0].clientY; isDragging.current = true }}
        onTouchMove={e => {
          if (!isDragging.current) return
          const dy = e.touches[0].clientY - startY.current
          if (dy > 60) onClose()
        }}
        onTouchEnd={() => { isDragging.current = false }}>
        {/* Drag handle */}
        <div className="flex justify-center pt-3 pb-1 shrink-0">
          <div className="w-10 h-1 rounded-full" style={{ background: 'var(--border)' }} />
        </div>
        <div className="overflow-y-auto flex-1 pb-8">
          {children}
        </div>
      </div>
    </div>
  )
}

// ── Course detail panel ───────────────────────────────────────────────────────
function CourseDetail({ course, groupId, onClose, onRefreshed }: {
  course: any; groupId: number | null; onClose: () => void; onRefreshed?: () => void
}) {
  const [activeTab, setActiveTab] = useState<string | null>(null)
  const router = useRouter()
  const { profile } = useScheduleStore()

  const { data: lessonsData, isLoading: lessonsLoading } = useQuery({
    queryKey: ['ecampus-lessons', course.Id, course.term_id, groupId],
    queryFn: () => authedFetch(`/course/${course.Id}/lessons?term_id=${course.term_id}${groupId ? `&group_id=${groupId}` : ''}`),
    staleTime: 300_000,
  })

  const { data: materialsData } = useQuery({
    queryKey: ['ecampus-materials', course.Id, course.term_id],
    queryFn: () => authedFetch(`/course/${course.Id}/materials?term_id=${course.term_id}`),
    staleTime: 600_000,
  })

  useEffect(() => {
    if (lessonsData?.lessons && !activeTab) {
      const firstKey = Object.keys(lessonsData.lessons)[0]
      if (firstKey) setActiveTab(firstKey)
    }
  }, [lessonsData]) // eslint-disable-line react-hooks/exhaustive-deps

  const currentLessons: any[] = (activeTab && lessonsData?.lessons?.[activeTab]) || []
  const allGradedCount = useMemo(() => {
    if (!lessonsData?.lessons) return 0
    return Object.values(lessonsData.lessons as Record<string, any[]>)
      .flat().filter((l: any) => l.GradeText?.trim()).length
  }, [lessonsData])

  return (
    <div className="flex flex-col gap-3 animate-fade-up">
      {/* Header */}
      <div className="px-5 pt-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-bold leading-snug mb-1" style={{ color: 'var(--t-primary)' }}>
              {course.Name}
            </h2>
            <p className="text-[11px]" style={{ color: 'var(--t-muted)' }}>{course.term_name}</p>
          </div>
          <button onClick={onClose} className="shrink-0 p-1.5 rounded-lg hover:bg-white/5"
            style={{ color: 'var(--t-muted)' }}>
            <X size={14} />
          </button>
        </div>

        {course.MaxRating > 0 && (
          <div className="mb-3">
            <div className="flex justify-between text-[11px] mb-1" style={{ color: 'var(--t-muted)' }}>
              <span>Рейтинг</span>
              <span className="font-mono font-semibold" style={{ color: 'var(--accent)' }}>
                {course.CurrentRating?.toFixed(2)} / {course.MaxRating}
              </span>
            </div>
            <div className="relative h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
              <div className="h-full rounded-full transition-all"
                style={{ width: `${Math.min(course.CurrentRating / course.MaxRating * 100, 100)}%`, background: 'var(--accent)' }} />
            </div>
          </div>
        )}

        {allGradedCount > 0 && (
          <div className="flex items-center gap-1.5 text-[11px] mb-3" style={{ color: '#34d399' }}>
            <CheckCircle size={11} /><span>{allGradedCount} оценок выставлено</span>
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {(course.LessonTypes || []).map((lt: any) => (
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
        <div className="px-5">
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--t-muted)' }}>
            Материалы
          </p>
          <div className="flex flex-wrap gap-1.5">
            {materialsData.materials.map((mat: any, i: number) => (
              mat.external ? (
                <a key={i} href={mat.url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] hover:opacity-80"
                  style={{ background: `${mat.color}15`, color: mat.color, border: `1px solid ${mat.color}25` }}>
                  {mat.icon} {mat.label}
                </a>
              ) : (
                <button key={i} onClick={() => downloadFile(mat.url, mat.label)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] hover:opacity-80"
                  style={{ background: `${mat.color}15`, color: mat.color, border: `1px solid ${mat.color}25` }}>
                  {mat.icon} {mat.label}
                </button>
              )
            ))}
          </div>
        </div>
      )}

      {/* Lessons */}
      {lessonsLoading ? (
        <div className="px-5 py-4 flex items-center gap-2" style={{ color: 'var(--t-muted)' }}>
          <Loader2 size={14} className="animate-spin" />
          <span className="text-xs">Загрузка занятий...</span>
        </div>
      ) : lessonsData?.lessons && Object.keys(lessonsData.lessons).length > 0 ? (
        <div className="px-5">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 size={13} style={{ color: 'var(--accent)' }} />
            <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>Занятия</span>
          </div>
          <div className="flex gap-1 mb-3 overflow-x-auto pb-1">
            {Object.entries(lessonsData.lessons as Record<string, any[]>).map(([typeName, ls]) => {
              const graded = ls.filter((l: any) => l.GradeText?.trim()).length
              return (
                <button key={typeName} onClick={() => setActiveTab(typeName)}
                  className="shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-medium"
                  style={{
                    background: activeTab === typeName ? 'var(--accent)' : 'var(--surface)',
                    color: activeTab === typeName ? 'var(--accent-fg)' : 'var(--t-secondary)',
                    border: `1px solid ${activeTab === typeName ? 'var(--accent)' : 'var(--border)'}`,
                  }}>
                  {typeName}{graded > 0 && <span className="ml-1 opacity-70">·{graded}</span>}
                </button>
              )
            })}
          </div>
          <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
            {currentLessons.map((lesson: any, i: number) => (
              <div key={lesson.Id || i}
                className="flex items-center gap-2 px-2.5 py-2 rounded-lg group hover:bg-white/3"
                style={{ background: 'var(--surface)' }}>
                <span className="shrink-0 text-[10px] font-mono w-14 tabular-nums" style={{ color: 'var(--t-muted)' }}>
                  {lesson.Date ? new Date(lesson.Date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) : '—'}
                </span>
                {lesson.Room && <span className="shrink-0 text-[10px]" style={{ color: 'var(--t-muted)' }}>{lesson.Room}</span>}
                <div className="flex-1" />
                {lesson.GradeText?.trim() && <GradeBadge grade={lesson.GradeText} />}
                {lesson.GainedScore > 0 && (
                  <span className="shrink-0 text-[10px] font-mono" style={{ color: '#34d399' }}>+{lesson.GainedScore.toFixed(1)}</span>
                )}
                {lesson.Date && groupId && profile?.groupId === groupId && (
                  <button
                    onClick={() => router.push(`/schedule?mode=group&id=${groupId}&name=${encodeURIComponent(profile?.groupName || '')}&date=${lesson.Date.split('T')[0]}`)}
                    className="shrink-0 opacity-0 group-hover:opacity-100 p-0.5 rounded">
                    <ExternalLink size={10} style={{ color: 'var(--accent)' }} />
                  </button>
                )}
              </div>
            ))}
            {currentLessons.length === 0 && (
              <div className="text-center py-6">
                <p className="text-[11px]" style={{ color: 'var(--t-muted)' }}>Занятия не проставлены</p>
                <p className="text-[10px] mt-1" style={{ color: 'var(--t-muted)', opacity: 0.6 }}>Обычно появляются в течение семестра</p>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}

// ── Term selector (горизонтальный скролл-пилюли) ─────────────────────────────
function TermSelector({
  termIds, coursesByTerm, selectedTerm, onSelect,
}: {
  termIds: number[]
  coursesByTerm: Record<number, any[]>
  selectedTerm: number | null
  onSelect: (tid: number) => void
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
      {termIds.map(tid => {
        const t = TERM_MAP[tid]
        const count = coursesByTerm[tid]?.length || 0
        const isActive = selectedTerm === tid
        return (
          <button key={tid} onClick={() => onSelect(tid)}
            className="shrink-0 flex flex-col items-center px-4 py-2.5 rounded-2xl transition-all"
            style={{
              background: isActive ? 'var(--accent)' : 'var(--card)',
              color: isActive ? 'var(--accent-fg)' : 'var(--t-secondary)',
              border: `1px solid ${isActive ? 'var(--accent)' : 'var(--border)'}`,
              minWidth: 72,
            }}>
            <span className="text-xs font-semibold">
              {t ? `${t.year} · ${t.sem} сем` : `${tid}`}
            </span>
            <span className="text-[9px] opacity-60 mt-0.5">{count} пр.</span>
          </button>
        )
      })}
    </div>
  )
}

// ── Quick filter chips ────────────────────────────────────────────────────────
type QuickFilter = 'exam' | 'credit' | 'grades' | 'coursework'

const QUICK_FILTERS: { key: QuickFilter; label: string; color: string }[] = [
  { key: 'exam',       label: 'Экзамен',    color: '#f87171' },
  { key: 'credit',     label: 'Зачёт',      color: '#fbbf24' },
  { key: 'grades',     label: 'Есть оценки', color: '#34d399' },
  { key: 'coursework', label: 'Курсовая',   color: '#a78bfa' },
]

function QuickFilters({
  active, onToggle,
}: {
  active: Set<QuickFilter>
  onToggle: (f: QuickFilter) => void
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
      {QUICK_FILTERS.map(({ key, label, color }) => {
        const isOn = active.has(key)
        return (
          <button key={key} onClick={() => onToggle(key)}
            className="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all"
            style={{
              background: isOn ? `${color}20` : 'var(--card)',
              color: isOn ? color : 'var(--t-secondary)',
              border: `1px solid ${isOn ? color + '50' : 'var(--border)'}`,
            }}>
            {label}
          </button>
        )
      })}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ECampusPage() {
  const { authToken, profile, clearNewGrades, updateGradeSnapshot } = useScheduleStore()
  const qc = useQueryClient()
  const router = useRouter()

  const [selectedTerm,   setSelectedTerm]   = useState<number | null>(null)
  const [selectedCourse, setSelectedCourse] = useState<any>(null)
  const [searchQuery,    setSearchQuery]     = useState('')
  const [searchAllTerms, setSearchAllTerms]  = useState(false)
  const [quickFilters,   setQuickFilters]    = useState<Set<QuickFilter>>(new Set())
  const [sortBy,         setSortBy]          = useState<'name' | 'rating' | 'grades' | 'recent'>('name')
  const [showSortMenu,   setShowSortMenu]    = useState(false)
  const [sheetOpen,      setSheetOpen]       = useState(false)

  // При открытии страницы предметов — сбрасываем бейдж
  useEffect(() => { clearNewGrades() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { data: status } = useQuery<any>({
    queryKey: ['ecampus-status'],
    queryFn: () => authedFetch('/status'),
    enabled: !!authToken,
    refetchInterval: (q) => q.state.data?.sync_status === 'running' ? 2000 : 30000,
  })

  const syncMutation = useMutation({
    mutationFn: () => authedFetch('/sync', { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ecampus-status'] })
      qc.invalidateQueries({ queryKey: ['ecampus-data'] })
    },
    onError: () => {
      qc.invalidateQueries({ queryKey: ['ecampus-status'] })
    },
  })

  const { data: ecampusData, isLoading } = useQuery<any>({
    queryKey: ['ecampus-data'],
    queryFn: () => authedFetch('/data'),
    enabled: !!authToken && !!status?.connected,
    staleTime: 60_000,
    refetchInterval: (status?.sync_status === 'running' || syncMutation.isPending) ? 2000 : false,
  })

  // Обновляем снапшот оценок при получении новых данных — вычисляем бейдж
  useEffect(() => {
    if (ecampusData?.courses?.length) {
      updateGradeSnapshot(ecampusData.courses)
    }
  }, [ecampusData?.courses]) // eslint-disable-line react-hooks/exhaustive-deps


  const isRunning = status?.sync_status === 'running'

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

  useEffect(() => {
    if (termIds.length && !selectedTerm) setSelectedTerm(termIds[termIds.length - 1])
  }, [termIds]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadingCourseIds = useMemo(() => {
    if (!isRunning || !ecampusData?.courses) return new Set<number>()
    return new Set(ecampusData.courses
      .filter((c: any) => !c.lessons || Object.keys(c.lessons).length === 0)
      .map((c: any) => c.Id))
  }, [ecampusData?.courses, isRunning])

  const toggleQuickFilter = useCallback((f: QuickFilter) => {
    setQuickFilters(prev => {
      const next = new Set(prev)
      if (next.has(f)) next.delete(f); else next.add(f)
      return next
    })
  }, [])

  // Поиск по всем семестрам или текущему
  const sourceCourses = useMemo(() => {
    if (searchQuery && searchAllTerms) return ecampusData?.courses || []
    return selectedTerm ? (coursesByTerm[selectedTerm] || []) : []
  }, [coursesByTerm, selectedTerm, searchQuery, searchAllTerms, ecampusData?.courses])

  const filteredCourses = useMemo(() => {
    let courses = [...sourceCourses]
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      courses = courses.filter(c => c.Name?.toLowerCase().includes(q))
    }
    if (quickFilters.has('exam'))
      courses = courses.filter(c => c.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType)))
    if (quickFilters.has('credit'))
      courses = courses.filter(c => c.LessonTypes?.some((lt: any) => CREDIT_TYPES.has(lt.LessonType)))
    if (quickFilters.has('grades'))
      courses = courses.filter(c => Object.values(c.lessons || {}).flat().some((l: any) => l.GradeText?.trim()))
    if (quickFilters.has('coursework'))
      courses = courses.filter(c => c.LessonTypes?.some((lt: any) => COURSE_WORK_TYPES.has(lt.LessonType)))

    if (sortBy === 'rating')
      courses.sort((a, b) => (b.CurrentRating || 0) - (a.CurrentRating || 0))
    else if (sortBy === 'grades') {
      const cnt = (c: any) => Object.values(c.lessons || {}).flat().filter((l: any) => l.GradeText?.trim()).length
      courses.sort((a, b) => cnt(b) - cnt(a))
    } else if (sortBy === 'recent') {
      // По дате последнего занятия
      const lastDate = (c: any) => {
        const dates = Object.values(c.lessons || {}).flat()
          .map((l: any) => l.Date).filter(Boolean).sort()
        return dates[dates.length - 1] || ''
      }
      courses.sort((a, b) => lastDate(b).localeCompare(lastDate(a)))
    } else {
      courses.sort((a, b) => (a.Name || '').localeCompare(b.Name || '', 'ru'))
    }
    return courses
  }, [sourceCourses, searchQuery, quickFilters, sortBy])

  const termStats = useMemo(() => {
    const courses = selectedTerm ? coursesByTerm[selectedTerm] || [] : []
    const withExam       = courses.filter(c => c.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType))).length
    const withCredit     = courses.filter(c =>
      c.LessonTypes?.some((lt: any) => CREDIT_TYPES.has(lt.LessonType)) &&
      !c.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType))
    ).length
    const withCourseWork = courses.filter(c => c.LessonTypes?.some((lt: any) => COURSE_WORK_TYPES.has(lt.LessonType))).length
    const withRating     = courses.filter(c => c.MaxRating > 0)
    const avgRating      = withRating.length
      ? withRating.reduce((s, c) => s + (c.CurrentRating || 0), 0) / withRating.length : 0
    const totalGrades    = courses.reduce((s, c) =>
      s + Object.values(c.lessons || {}).flat().filter((l: any) => l.GradeText?.trim()).length, 0)
    return { total: courses.length, withExam, withCredit, withCourseWork, avgRating, totalGrades }
  }, [coursesByTerm, selectedTerm])

  const SORT_LABELS: Record<string, string> = {
    name:   'По названию',
    rating: 'По рейтингу',
    grades: 'По оценкам',
    recent: 'По актуальности',
  }

  const handleCourseClick = (course: any) => {
    if (selectedCourse?.Id === course.Id && selectedCourse?.term_id === course.term_id) {
      setSelectedCourse(null)
      setSheetOpen(false)
    } else {
      setSelectedCourse(course)
      setSheetOpen(true)
    }
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

  if (!isLoading && status && !status.connected) {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Предметы" />
        <div className="card px-5 py-10 text-center mt-4">
          <GraduationCap size={36} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm font-semibold mb-1" style={{ color: 'var(--t-primary)' }}>eCampus не подключён</p>
          <p className="text-xs mb-4" style={{ color: 'var(--t-muted)' }}>Подключите eCampus в разделе Профиль</p>
          <a href="/profile" className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold"
            style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
            Перейти в профиль
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 lg:px-0 pb-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <PageHeader title="Предметы" />
        <div className="flex items-center gap-2">
          {status?.last_sync && !isRunning && (
            <span className="text-[11px]" style={{ color: 'var(--t-muted)' }}>
              {new Date(status.last_sync).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}
            </span>
          )}
          <button onClick={() => syncMutation.mutate()} disabled={isRunning || syncMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] hover:bg-white/5 disabled:opacity-40"
            style={{ color: 'var(--accent)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}>
            <RefreshCw size={11} className={isRunning ? 'animate-spin' : ''} />
            Обновить
          </button>
        </div>
      </div>

      {/* Sync progress */}
      <SyncProgressBar status={status} />

      {isLoading && !ecampusData ? (
        <div className="flex flex-col gap-3">
          {[1, 2, 3, 4].map(i => <div key={i} className="card h-16 animate-pulse" />)}
        </div>
      ) : ecampusData ? (
        <div className="flex flex-col gap-4">

          {/* Выбор семестра — горизонтальный скролл */}
          <TermSelector termIds={termIds} coursesByTerm={coursesByTerm} selectedTerm={selectedTerm}
            onSelect={(tid) => { setSelectedTerm(tid); setSelectedCourse(null); setSheetOpen(false) }} />

          {/* Статистика */}
          {selectedTerm && (
            <div className="grid grid-cols-4 gap-2">
              {[
                { label: 'Всего',       value: termStats.total,                                             icon: BookMarked, color: 'var(--accent)' },
                { label: 'Оценок',      value: termStats.totalGrades,                                       icon: Award,      color: '#34d399' },
                { label: 'Ср. рейтинг', value: termStats.avgRating > 0 ? termStats.avgRating.toFixed(1) : '—', icon: TrendingUp, color: '#fbbf24' },
                { label: 'Курс. работ', value: termStats.withCourseWork,                                    icon: FileText,   color: '#a78bfa' },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="card px-3 py-2.5 text-center">
                  <Icon size={13} className="mx-auto mb-1" style={{ color }} />
                  <div className="text-sm font-bold tabular-nums" style={{ color }}>{value}</div>
                  <div className="text-[9px] mt-0.5" style={{ color: 'var(--t-muted)' }}>{label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Поиск */}
          <div className="flex flex-col gap-2">
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: 'var(--t-muted)' }} />
              <input type="text" placeholder="Поиск предмета..." value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="input-search w-full pl-9 pr-8 text-sm" />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                  <X size={12} style={{ color: 'var(--t-muted)' }} />
                </button>
              )}
            </div>

            {/* Поиск по всем семестрам */}
            {searchQuery && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSearchAllTerms(v => !v)}
                  className="flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-lg"
                  style={{
                    background: searchAllTerms ? 'var(--accent-dim)' : 'var(--card)',
                    color: searchAllTerms ? 'var(--accent)' : 'var(--t-muted)',
                    border: `1px solid ${searchAllTerms ? 'var(--accent)' : 'var(--border)'}`,
                  }}>
                  {searchAllTerms ? '✓' : ''} Во всех семестрах
                </button>
                {searchAllTerms && (
                  <span className="text-[10px]" style={{ color: 'var(--t-muted)' }}>
                    найдено {filteredCourses.length}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Быстрые фильтры + сортировка */}
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <QuickFilters active={quickFilters} onToggle={toggleQuickFilter} />
            </div>
            {/* Сортировка */}
            <div className="relative shrink-0">
              <button onClick={() => setShowSortMenu(v => !v)}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px]"
                style={{ color: 'var(--t-secondary)', border: '1px solid var(--border)', background: 'var(--card)' }}>
                {SORT_LABELS[sortBy].split(' ')[1] ?? SORT_LABELS[sortBy]}
                {showSortMenu ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              </button>
              {showSortMenu && (
                <div className="absolute right-0 top-full mt-1 z-20 rounded-xl overflow-hidden shadow-lg"
                  style={{ background: 'var(--card)', border: '1px solid var(--border)', minWidth: 140 }}>
                  {Object.entries(SORT_LABELS).map(([key, label]) => (
                    <button key={key}
                      onClick={() => { setSortBy(key as any); setShowSortMenu(false) }}
                      className="w-full text-left px-3 py-2 text-xs hover:bg-white/5"
                      style={{ color: sortBy === key ? 'var(--accent)' : 'var(--t-primary)' }}>
                      {label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Список курсов + Desktop detail */}
          <div className="lg:grid lg:grid-cols-2 lg:gap-4">
            <div className="flex flex-col gap-1.5">
              {filteredCourses.length === 0 ? (
                <div className="card px-5 py-8 text-center">
                  {isRunning
                    ? <div className="flex flex-col items-center gap-3"><CourseSpinner />
                        <p className="text-sm" style={{ color: 'var(--t-muted)' }}>Загружаем предметы...</p></div>
                    : <><Search size={24} className="mx-auto mb-2 opacity-30" />
                        <p className="text-sm" style={{ color: 'var(--t-muted)' }}>Предметы не найдены</p>
                        {quickFilters.size > 0 && (
                          <button onClick={() => setQuickFilters(new Set())}
                            className="text-xs mt-2" style={{ color: 'var(--accent)' }}>
                            Сбросить фильтры
                          </button>
                        )}</>
                  }
                </div>
              ) : filteredCourses.map((course: any) => {
                const isSelected  = selectedCourse?.Id === course.Id && selectedCourse?.term_id === course.term_id
                const isLoading   = loadingCourseIds.has(course.Id)
                const gradeCount  = Object.values(course.lessons || {}).flat()
                  .filter((l: any) => l.GradeText?.trim()).length

                return (
                  <button key={`${course.Id}-${course.term_id}`}
                    onClick={() => handleCourseClick(course)}
                    className="w-full text-left px-4 py-3 rounded-xl transition-all"
                    style={{
                      background: isSelected ? 'color-mix(in srgb, var(--accent) 10%, transparent)' : 'var(--card)',
                      border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                      opacity: isLoading ? 0.7 : 1,
                    }}>
                    <div className="flex items-start gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-medium leading-snug truncate"
                          style={{ color: isSelected ? 'var(--accent)' : 'var(--t-primary)' }}>
                          {course.Name}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                          {/* Семестр если ищем по всем */}
                          {searchAllTerms && searchQuery && course.term_name && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded"
                              style={{ background: 'var(--surface)', color: 'var(--t-muted)' }}>
                              {course.term_name}
                            </span>
                          )}
                          {(course.LessonTypes || []).slice(0, 3).map((lt: any) => (
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
                        {isLoading && <CourseSpinner />}
                        {!isLoading && course.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType)) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ background: '#f8717115', color: '#f87171' }}>Экзамен</span>
                        )}
                        {!isLoading && course.LessonTypes?.some((lt: any) => CREDIT_TYPES.has(lt.LessonType)) &&
                          !course.LessonTypes?.some((lt: any) => EXAM_TYPES.has(lt.LessonType)) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ background: '#fbbf2415', color: '#fbbf24' }}>
                            {course.LessonTypes?.some((lt: any) => lt.LessonType === 55) ? 'Диф.зачёт' : 'Зачёт'}
                          </span>
                        )}
                        {!isLoading && gradeCount > 0 && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ background: '#34d39915', color: '#34d399' }}>
                            {gradeCount} оц.
                          </span>
                        )}
                        {!isLoading && course.MaxRating > 0 && (
                          <span className="text-[10px] font-mono font-semibold tabular-nums"
                            style={{
                              color: course.CurrentRating / course.MaxRating >= 0.7 ? '#34d399'
                                : course.CurrentRating / course.MaxRating >= 0.4 ? '#fbbf24' : '#f87171',
                            }}>
                            {course.CurrentRating?.toFixed(0)}/{course.MaxRating}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                )
              })}

              <p className="text-center text-[11px] py-2" style={{ color: 'var(--t-muted)' }}>
                {filteredCourses.length} из {searchAllTerms && searchQuery
                  ? (ecampusData?.courses?.length || 0)
                  : (coursesByTerm[selectedTerm || 0]?.length || 0)
                } предметов
                {isRunning && status?.sync_courses_found > 0 && (
                  <span style={{ color: 'var(--accent)' }}> · всего найдено {status.sync_courses_found}</span>
                )}
              </p>
            </div>

            {/* Desktop: детали справа */}
            {selectedCourse && (
              <div className="mt-4 lg:mt-0 hidden lg:block">
                <div className="card pb-4">
                  <CourseDetail course={selectedCourse} groupId={profile?.groupId ?? null}
                    onClose={() => { setSelectedCourse(null) }} />
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="card px-5 py-8 text-center">
          <p className="text-sm" style={{ color: 'var(--t-muted)' }}>
            {isRunning ? 'Синхронизация...' : 'Нет данных. Нажмите «Обновить».'}
          </p>
        </div>
      )}

      {/* Mobile: bottom sheet */}
      <BottomSheet open={sheetOpen && !!selectedCourse} onClose={() => { setSheetOpen(false); setSelectedCourse(null) }}>
        {selectedCourse && (
          <CourseDetail course={selectedCourse} groupId={profile?.groupId ?? null}
            onClose={() => { setSheetOpen(false); setSelectedCourse(null) }} />
        )}
      </BottomSheet>
    </div>
  )
}
