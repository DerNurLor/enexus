'use client'

import { useState, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, CalendarRange, X } from 'lucide-react'
import { format } from 'date-fns'
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

export default function SchedulePage() {
  const { mode, groupId, groupName, teacherId, teacherName, roomId, roomName, setMode } = useScheduleStore()
  const [query, setQuery]               = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date())
  const inputRef = useRef<HTMLInputElement>(null)

  const entityId   = mode === 'group' ? groupId   : mode === 'teacher' ? teacherId   : roomId
  const entityName = mode === 'group' ? groupName : mode === 'teacher' ? teacherName : roomName
  const dateStr    = format(selectedDate, 'yyyy-MM-dd')

  const { data: dayData, isLoading, isFetching } = useQuery({
    queryKey: ['schedule', 'day', mode, entityId, dateStr],
    queryFn:  () => entityId && mode === 'group' ? api.getGroupDay(entityId, dateStr) : null,
    enabled:  !!entityId && mode === 'group',
  })

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

  const lessons: Lesson[] = dayData?.lessons || []

  function handleModeChange(m: SearchMode) {
    setMode(m)
    setQuery('')
    setShowDropdown(false)
  }

  return (
    <div className="px-4 lg:px-0">
      <PageHeader
        title="Расписание"
        action={
          <button className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
            <CalendarRange size={18} style={{ color: 'var(--t-secondary)' }} />
          </button>
        }
      />

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
        </div>
      ) : (isLoading || isFetching) ? (
        <div className="flex flex-col gap-3">
          {[1,2,3].map(i => (
            <div key={i} className="card h-20 animate-pulse" style={{ opacity: 0.5 }} />
          ))}
        </div>
      ) : lessons.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3">
          <CalendarRange size={40} style={{ color: 'var(--t-muted)' }} />
          <span className="text-sm" style={{ color: 'var(--t-muted)' }}>
            {dayData?.message || 'Занятий нет'}
          </span>
        </div>
      ) : (
        <div className="flex flex-col gap-3 stagger">
          {lessons.map((lesson, i) => (
            <LessonCard key={i} lesson={{
              id:        String(i),
              subject:   lesson.subject,
              type:      mapLessonType(lesson.lesson_type),
              teacher:   lesson.teacher_name || '—',
              room:      lesson.classroom || lesson.room_name || '—',
              timeStart: lesson.time_start,
              timeEnd:   lesson.time_end,
              subgroup:  lesson.subgroup ?? undefined,
              note:      lesson.note ?? undefined,
            }} />
          ))}
        </div>
      )}
    </div>
  )
}
