import { MapPin, User } from 'lucide-react'
import clsx from 'clsx'

export type LessonType = 'lab' | 'lecture' | 'seminar' | 'practice'

export interface Lesson {
  id: string
  subject: string
  type: LessonType
  teacher: string
  room: string
  timeStart: string
  timeEnd: string
}

const TYPE_CONFIG: Record<LessonType, { label: string; color: string; bg: string }> = {
  lab:      { label: 'Лаб',      color: '#4ade80', bg: 'rgba(74,222,128,0.12)' },
  lecture:  { label: 'Лекция',   color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  seminar:  { label: 'Семинар',  color: '#fb923c', bg: 'rgba(251,146,60,0.12)' },
  practice: { label: 'Практика', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
}

export function LessonCard({ lesson }: { lesson: Lesson }) {
  const cfg = TYPE_CONFIG[lesson.type]

  return (
    <div
      className="card flex gap-0 overflow-hidden"
      style={{ borderLeft: `3px solid ${cfg.color}` }}
    >
      {/* Time */}
      <div className="flex flex-col justify-center px-4 py-4 min-w-[72px]">
        <span className="text-sm font-bold tabular-nums" style={{ color: 'var(--t-primary)' }}>
          {lesson.timeStart}
        </span>
        <span className="text-xs tabular-nums mt-0.5" style={{ color: 'var(--t-muted)' }}>
          {lesson.timeEnd}
        </span>
      </div>

      {/* Divider */}
      <div className="w-px my-4" style={{ background: cfg.color, opacity: 0.4 }} />

      {/* Content */}
      <div className="flex-1 px-4 py-4 min-w-0">
        <div className="flex items-start justify-between gap-2 mb-2">
          <span className="text-sm font-semibold leading-tight" style={{ color: 'var(--t-primary)' }}>
            {lesson.subject}
          </span>
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-md whitespace-nowrap flex-shrink-0"
            style={{ color: cfg.color, background: cfg.bg }}
          >
            {cfg.label}
          </span>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1">
            <User size={11} style={{ color: 'var(--t-muted)' }} />
            <span className="text-xs" style={{ color: 'var(--t-secondary)' }}>{lesson.teacher}</span>
          </div>
          <div className="flex items-center gap-1">
            <MapPin size={11} style={{ color: 'var(--t-muted)' }} />
            <span className="text-xs" style={{ color: 'var(--t-secondary)' }}>{lesson.room}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
