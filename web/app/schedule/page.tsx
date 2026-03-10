'use client'

import { useState } from 'react'
import { Search, CalendarRange } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { PillTabs } from '@/components/ui/PillTabs'
import { DayPicker } from '@/components/schedule/DayPicker'
import { LessonCard, Lesson } from '@/components/schedule/LessonCard'

type SearchMode = 'group' | 'teacher' | 'room'

// Mock data — replace with real API calls
const MOCK_LESSONS: Lesson[] = [
  { id: '1', subject: 'Системное программирование', type: 'lab',      teacher: 'Проф. Сидорова К.М.', room: 'А-308', timeStart: '09:00', timeEnd: '10:35' },
  { id: '2', subject: 'Дискретная математика',      type: 'lecture',  teacher: 'Доц. Бондарь В.Я.',   room: 'Б-105', timeStart: '10:45', timeEnd: '12:20' },
  { id: '3', subject: 'Операционные системы',        type: 'seminar',  teacher: 'Асс. Коваль П.С.',    room: 'В-301', timeStart: '13:30', timeEnd: '15:05' },
]

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

export default function SchedulePage() {
  const [mode, setMode] = useState<SearchMode>('group')
  const [query, setQuery] = useState('')
  const [selectedDate, setSelectedDate] = useState(new Date())

  return (
    <div className="px-4 lg:px-0">
      <PageHeader
        title="Расписание"
        action={
          <button
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
          >
            <CalendarRange size={18} style={{ color: 'var(--t-secondary)' }} />
          </button>
        }
      />

      {/* Search mode pills */}
      <div className="mb-3">
        <PillTabs options={SEARCH_MODES} value={mode} onChange={setMode} />
      </div>

      {/* Search input */}
      <div className="relative mb-4">
        <Search
          size={16}
          className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none"
          style={{ color: 'var(--t-muted)' }}
        />
        <input
          className="input-search pl-10"
          placeholder={PLACEHOLDER[mode]}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {/* Day picker */}
      <div className="mb-5">
        <DayPicker selected={selectedDate} onSelect={setSelectedDate} />
      </div>

      {/* Lessons */}
      <div className="flex flex-col gap-3 stagger">
        {MOCK_LESSONS.length === 0 ? (
          <div className="flex flex-col items-center py-16 gap-3">
            <CalendarRange size={40} style={{ color: 'var(--t-muted)' }} />
            <span className="text-sm" style={{ color: 'var(--t-muted)' }}>Занятий нет</span>
          </div>
        ) : (
          MOCK_LESSONS.map((lesson) => (
            <LessonCard key={lesson.id} lesson={lesson} />
          ))
        )}
      </div>
    </div>
  )
}
