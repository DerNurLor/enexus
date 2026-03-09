import { useState, useRef, useCallback, useEffect } from 'react'
import { api } from '../utils/api'
import { getDateRange, isoToday, fmtDate, LT_KEY, LT_SHORT, DateQuick } from '../utils/helpers'
import type {
  SearchType, ScheduleResponse, Day, Lesson, SearchResult, Settings, Favorite
} from '../types'
import { IconSearch } from '../components/Icons'

interface Props {
  isActive: boolean
  settings: Settings
  favorites: Favorite[]
  onAddFav: (type: SearchType, id: string, name: string) => void
  toast: (msg: string) => void
}

interface AutoItem {
  type: SearchType
  id: string
  name: string
  sub?: string
}

export function SchedulePage({ settings, favorites, onAddFav, toast, isActive }: Props) {
  const [searchType, setSearchType] = useState<SearchType>('group')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<AutoItem | null>(null)
  const [acItems, setAcItems] = useState<AutoItem[]>([])
  const [acVisible, setAcVisible] = useState(false)
  const [dateFrom, setDateFrom] = useState(isoToday())
  const [dateTo, setDateTo] = useState(isoToday())
  const [activeQuick, setActiveQuick] = useState<DateQuick>('today')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScheduleResponse | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const applyDateQuick = useCallback((q: DateQuick) => {
    const { from, to } = getDateRange(q)
    setDateFrom(from)
    setDateTo(to)
    setActiveQuick(q)
  }, [])

  // init today
  useEffect(() => {
    const today = isoToday()
    setDateFrom(today)
    setDateTo(today)
  }, [])

  // Listen for room open event from RoomsPage
  useEffect(() => {
    const handler = (e: Event) => {
      const room = (e as CustomEvent<string>).detail
      setSearchType('room')
      setQuery(room)
      setSelected({ type: 'room', id: room, name: room })
      setAcVisible(false)
      applyDateQuick('today')
      // Trigger search after state update
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('_doSearch'))
      }, 50)
    }
    window.addEventListener('openRoom', handler)
    return () => window.removeEventListener('openRoom', handler)
  }, [applyDateQuick])

  // Listen for loadFavorite event from FavoritesPage
  useEffect(() => {
    const handler = (e: Event) => {
      const fav = (e as CustomEvent<Favorite>).detail
      setSearchType(fav.type)
      setQuery(fav.label)
      setSelected({ type: fav.type, id: fav.id, name: fav.label })
      setAcVisible(false)
      applyDateQuick('week')
    }
    window.addEventListener('loadFavorite', handler)
    return () => window.removeEventListener('loadFavorite', handler)
  }, [applyDateQuick])

  const fetchAc = useCallback(async (q: string) => {
    try {
      const data = await api<SearchResult>(`/miniapp/api/search?q=${encodeURIComponent(q)}`)
      let items: AutoItem[] = []
      if (searchType === 'group')
        items = (data.groups ?? []).slice(0, 8).map(g => ({
          type: 'group', id: String(g.groupId), name: g.name, sub: g.instituteName,
        }))
      else if (searchType === 'teacher')
        items = (data.teachers ?? []).slice(0, 8).map(t => ({
          type: 'teacher', id: String(t.teacherId), name: t.fullName, sub: t.shortName,
        }))
      else
        items = (data.rooms ?? []).slice(0, 8).map(r => ({
          type: 'room', id: String(r.roomId), name: r.name, sub: r.building,
        }))
      setAcItems(items)
      setAcVisible(items.length > 0)
    } catch { /* silent */ }
  }, [searchType])

  const onInput = useCallback((val: string) => {
    setQuery(val)
    setSelected(null)
    clearTimeout(timerRef.current)
    if (val.length < 2) { setAcVisible(false); return }
    timerRef.current = setTimeout(() => fetchAc(val), 280)
  }, [fetchAc])

  const selectItem = useCallback((item: AutoItem) => {
    setSelected(item)
    setQuery(item.name)
    setAcVisible(false)
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
  }, [])

  const doSearch = useCallback(async () => {
    const name = selected?.name ?? query.trim()
    if (!name) { toast('Введите название для поиска'); return }
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium')
    setLoading(true)
    setResult(null)
    try {
      const params = new URLSearchParams()
      if (searchType === 'group') params.set('group_name', name)
      if (searchType === 'teacher') params.set('teacher_name', name)
      if (searchType === 'room') params.set('room_name', name)
      if (dateFrom) params.set('from_date', dateFrom)
      if (dateTo) params.set('to_date', dateTo)
      const data = await api<ScheduleResponse>(`/miniapp/api/schedule?${params}`)
      setResult(data)
    } catch (e) {
      toast((e as Error).message ?? 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }, [selected, query, searchType, dateFrom, dateTo, toast])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { setAcVisible(false); doSearch() }
  }, [doSearch])

  const isInFav = selected
    ? favorites.some(f => f.type === searchType && f.id === (selected?.id ?? ''))
    : false

  const PLACEHOLDERS: Record<SearchType, string> = {
    group: 'Группа: ИСС-б-о-22-3',
    teacher: 'Фамилия И.О.',
    room: 'Аудитория 301',
  }

  return (
    <div id="page-schedule" className={`page${isActive ? " active" : ""}`}>
      <div className="sec-head">РАСПИСАНИЕ</div>
      <div className="sec-subhead">Поиск по группам, преподавателям, аудиториям</div>

      {/* Search type chips */}
      <div className="chip-row">
        {(['group', 'teacher', 'room'] as SearchType[]).map(t => (
          <button
            key={t}
            className={`chip${searchType === t ? ' active' : ''}`}
            onClick={() => {
              setSearchType(t)
              setSelected(null)
              setQuery('')
              setAcVisible(false)
              setResult(null)
            }}
          >
            {t === 'group' ? 'Группа' : t === 'teacher' ? 'Преподаватель' : 'Аудитория'}
          </button>
        ))}
      </div>

      {/* Search input */}
      <div className="autocomplete-wrap" style={{ marginBottom: 10 }}>
        <div className="input-group" style={{ marginBottom: 0 }}>
          <IconSearch className="input-icon" size={15} />
          <input
            type="text"
            value={query}
            placeholder={PLACEHOLDERS[searchType]}
            autoComplete="off"
            onChange={e => onInput(e.target.value)}
            onFocus={() => { if (acItems.length) setAcVisible(true) }}
            onBlur={() => setTimeout(() => setAcVisible(false), 180)}
            onKeyDown={handleKeyDown}
          />
        </div>
        {acVisible && acItems.length > 0 && (
          <div className="autocomplete-list">
            {acItems.map((it, i) => (
              <div
                key={i}
                className="autocomplete-item"
                onMouseDown={() => selectItem(it)}
              >
                {it.name}
                {it.sub && <span className="autocomplete-item-sub">{it.sub}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Date range */}
      <div className="date-grid" style={{ marginBottom: 10 }}>
        <div>
          <div className="field-label">С</div>
          <input
            type="date"
            value={dateFrom}
            onChange={e => { setDateFrom(e.target.value); setActiveQuick('' as DateQuick) }}
          />
        </div>
        <div>
          <div className="field-label">По</div>
          <input
            type="date"
            value={dateTo}
            onChange={e => { setDateTo(e.target.value); setActiveQuick('' as DateQuick) }}
          />
        </div>
      </div>

      {/* Quick date chips */}
      <div className="chip-row">
        {([['today', 'Сегодня'], ['tomorrow', 'Завтра'], ['week', 'Неделя'], ['next-week', 'Сл. неделя']] as [DateQuick, string][]).map(([q, label]) => (
          <button
            key={q}
            className={`chip${activeQuick === q ? ' active' : ''}`}
            onClick={() => applyDateQuick(q)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Search button */}
      <button
        className="btn btn-primary mt-12"
        onClick={doSearch}
        disabled={loading}
      >
        {loading ? <span className="spinner" /> : (
          <IconSearch size={15} />
        )}
        {loading ? 'Поиск…' : 'Показать расписание'}
      </button>

      {/* Results */}
      <div id="results-panel" style={{ marginTop: 20 }}>
        {loading && (
          <div className="loading-center"><span className="spinner" /></div>
        )}
        {!loading && result && (
          <ScheduleResult
            data={result}
            name={selected?.name ?? query}
            type={searchType}
            selectedId={selected?.id ?? ''}
            settings={settings}
            isInFav={isInFav}
            onFav={() => {
              if (!selected) return
              onAddFav(searchType, selected.id, selected.name)
            }}
            onRoomClick={(room) => {
              // handled by parent via event
              const evt = new CustomEvent('openRoom', { detail: room })
              window.dispatchEvent(evt)
            }}
          />
        )}
      </div>
    </div>
  )
}

interface ResultProps {
  data: ScheduleResponse
  name: string
  type: SearchType
  selectedId: string
  settings: Settings
  isInFav: boolean
  onFav: () => void
  onRoomClick: (room: string) => void
}

function ScheduleResult({ data, name, settings, isInFav, onFav }: ResultProps) {
  const days = data.days ?? []
  const total = data.meta?.total ?? 0

  if (!days.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📭</div>
        <div className="empty-title">НЕТ ЗАНЯТИЙ</div>
        <div className="empty-desc">За выбранный период расписание отсутствует</div>
      </div>
    )
  }

  return (
    <>
      <div className="results-header">
        <span className="results-count">{total} занятий · {name}</span>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onFav}
          style={{ width: 'auto', gap: 5 }}
        >
          {isInFav ? '★' : '☆'} Избранное
        </button>
      </div>
      {days.map((day: Day) => (
        <DayBlock key={day.date} day={day} compact={settings.compact} />
      ))}
    </>
  )
}

function DayBlock({ day, compact }: { day: Day; compact?: boolean }) {
  const lessons = day.lessons ?? []
  if (!lessons.length) return null
  return (
    <div className="day-block">
      <div className="day-label">
        {fmtDate(day.date)}
        <span className="day-label-meta">Нед. {day.weekNumber ?? '—'}</span>
      </div>
      {lessons.map((l: Lesson, i: number) => (
        <LessonCard key={i} lesson={l} compact={compact} index={i} />
      ))}
    </div>
  )
}

function LessonCard({ lesson: l, compact, index }: { lesson: Lesson; compact?: boolean; index: number }) {
  const ltKey = LT_KEY[l.lessonType ?? ''] ?? 'lec'
  const ltShort = LT_SHORT[l.lessonType ?? ''] ?? ''

  return (
    <div
      className={`lesson-card type-${ltKey}`}
      style={{ animationDelay: `${index * 0.04}s` }}
    >
      {ltShort && (
        <div className={`lesson-badge badge-${ltKey}`}>{ltShort}</div>
      )}
      <div className="lesson-time">{l.timeStart} — {l.timeEnd}</div>
      <div className="lesson-subj">{l.subject}</div>
      {!compact && (
        <div className="lesson-meta">
          {l.roomName && <span className="lesson-meta-item">🚪 {l.roomName}</span>}
          {l.teacherName && <span className="lesson-meta-item">👤 {l.teacherName}</span>}
          {l.groupName && <span className="lesson-meta-item">👥 {l.groupName}</span>}
          {l.building && <span className="lesson-meta-item">🏛 {l.building}</span>}
          {l.subgroup && <span className="lesson-meta-item">Пгр.{l.subgroup}</span>}
        </div>
      )}
    </div>
  )
}
