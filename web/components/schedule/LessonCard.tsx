'use client'

import { useState, useRef, useCallback } from 'react'
import { useGestures } from '@/hooks/useGestures'
import { MapPin, User, Users } from 'lucide-react'
import { useScheduleStore } from '@/lib/store'

export type LessonType = 'lab' | 'lecture' | 'seminar' | 'practice' | 'exam' | 'credit' | 'consultation'

export interface LessonCardData {
  id:           string
  subject:      string
  type:         LessonType
  teacher:      string
  teacherId?:   number | null
  showTeacher?: boolean
  room:         string
  roomId?:      number | null
  showRoom?:    boolean
  groupName?:   string | null
  groupNames?:  string[] | null
  groups?:      { id: number; name: string }[] | null
  groupId?:     number | null
  timeStart:    string
  timeEnd:      string
  subgroup?:    string
  note?:        string
  grade?:       string | null
}

const TYPE_CONFIG: Record<LessonType, { label: string; color: string; bg: string }> = {
  lab:          { label: 'Лаб',         color: '#4ade80', bg: 'rgba(74,222,128,0.12)' },
  lecture:      { label: 'Лекция',      color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  seminar:      { label: 'Семинар',     color: '#fb923c', bg: 'rgba(251,146,60,0.12)' },
  practice:     { label: 'Практика',    color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  exam:         { label: 'Экзамен',     color: '#f87171', bg: 'rgba(248,113,113,0.12)' },
  credit:       { label: 'Зачёт',       color: '#fbbf24', bg: 'rgba(251,191,36,0.12)' },
  consultation: { label: 'Консультация',color: '#34d399', bg: 'rgba(52,211,153,0.12)' },
}

export function LessonCard({ lesson }: { lesson: LessonCardData }) {
  const cfg = TYPE_CONFIG[lesson.type]
  const { setTeacher, setRoom, setGroup, setMode } = useScheduleStore()
  const [pressed,   setPressed]   = useState(false)
  const [copied,    setCopied]    = useState(false)

  const cardGestures = useGestures({
    // Long press — копировать предмет в буфер
    onLongPress: () => {
      navigator.clipboard?.writeText(lesson.subject).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      })
    },
    // Double tap — перейти к аудитории
    onDoubleTap: () => {
      if (lesson.roomId && lesson.room) {
        if ('vibrate' in navigator) navigator.vibrate([8, 30, 8])
        const store = useScheduleStore.getState()
        store.setMode('room')
        store.setRoom(lesson.roomId, lesson.room)
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
    },
    swipeThreshold: 80,
  })

  const showTeacher = lesson.showTeacher !== false
  const showRoom    = lesson.showRoom    !== false

  const groups: { id: number; name: string }[] =
    lesson.groups && lesson.groups.length > 0
      ? lesson.groups
      : lesson.groupId && lesson.groupName
        ? [{ id: lesson.groupId, name: lesson.groupName }]
        : []

  const showGroupRow = groups.length > 0

  function handleTeacherClick(e: React.MouseEvent) {
    if (!lesson.teacherId) return
    e.stopPropagation()
    setMode('teacher'); setTeacher(lesson.teacherId, lesson.teacher)
    window.scrollTo({ top: 0, behavior: 'smooth' })
    if ('vibrate' in navigator) navigator.vibrate(6)
  }
  function handleRoomClick(e: React.MouseEvent) {
    if (!lesson.roomId) return
    e.stopPropagation()
    setMode('room'); setRoom(lesson.roomId, lesson.room)
    window.scrollTo({ top: 0, behavior: 'smooth' })
    if ('vibrate' in navigator) navigator.vibrate(6)
  }
  function handleGroupClick(e: React.MouseEvent, id: number, name: string) {
    e.stopPropagation()
    setMode('group'); setGroup(id, name)
    window.scrollTo({ top: 0, behavior: 'smooth' })
    if ('vibrate' in navigator) navigator.vibrate(6)
  }

  const hasTeacherLink = showTeacher && !!lesson.teacherId
  const hasRoomLink    = showRoom    && !!lesson.roomId

  return (
    <div
      className="card flex gap-0 overflow-hidden card-lift ripple-container"
      style={{
        borderLeft: `3px solid ${cfg.color}`,
        transform: pressed ? 'scale(0.98)' : undefined,
        transition: 'transform 0.12s var(--snap, ease)',
        position: 'relative',
      }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      onTouchStart={(e) => { setPressed(true); cardGestures.onTouchStart(e) }}
      onTouchMove={cardGestures.onTouchMove}
      onTouchEnd={(e)   => { setPressed(false); cardGestures.onTouchEnd(e) }}
    >
      {/* Copied feedback toast */}
      {copied && (
        <div className="absolute inset-x-0 top-0 flex items-center justify-center z-10 pointer-events-none">
          <span className="text-[10px] font-semibold px-2 py-1 rounded-full badge-pop"
            style={{ background: cfg.color, color: '#000', marginTop: 4 }}>
            Скопировано ✓
          </span>
        </div>
      )}
      {/* Time column */}
      <div className="flex flex-col justify-center px-4 py-4 min-w-[72px]">
        <span className="text-sm font-bold tabular-nums" style={{ color: 'var(--t-primary)' }}>
          {lesson.timeStart}
        </span>
        <span className="text-xs tabular-nums mt-0.5" style={{ color: 'var(--t-muted)' }}>
          {lesson.timeEnd}
        </span>
      </div>

      {/* Animated left border glow */}
      <div className="w-px my-4" style={{ background: cfg.color, opacity: 0.4 }} />

      {/* Content */}
      <div className="flex-1 px-4 py-4 min-w-0">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex-1 min-w-0">
            <span className="text-sm font-semibold leading-tight" style={{ color: 'var(--t-primary)' }}>
              {lesson.subject}
              {lesson.grade && (
                <span className="ml-2 text-[10px] font-semibold px-1.5 py-0.5 rounded badge-pop"
                  style={{
                    background: lesson.grade === 'отлично' ? '#10b98120' : lesson.grade === 'хорошо' ? '#3b82f620' : '#f59e0b20',
                    color:      lesson.grade === 'отлично' ? '#10b981'   : lesson.grade === 'хорошо' ? '#3b82f6'   : '#f59e0b',
                  }}>
                  {lesson.grade}
                </span>
              )}
            </span>
            {lesson.subgroup && (
              <span className="ml-2 text-[10px]" style={{ color: 'var(--t-muted)' }}>
                {lesson.subgroup}
              </span>
            )}
          </div>
          {/* Type badge — tap scale */}
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md whitespace-nowrap flex-shrink-0 tap-scale"
            style={{ color: cfg.color, background: cfg.bg }}>
            {cfg.label}
          </span>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {showTeacher && lesson.teacher && lesson.teacher !== '—' && (
            <div className="flex items-center gap-1">
              <User size={11} style={{ color: 'var(--t-muted)' }} />
              <button onClick={hasTeacherLink ? handleTeacherClick : undefined}
                className={`text-xs transition-colors ${hasTeacherLink ? 'hover:text-[var(--cyan)] cursor-pointer underline-offset-2 hover:underline tap-scale' : 'cursor-default'}`}
                style={{ color: 'var(--t-secondary)', background: 'none', border: 'none', padding: 0 }}>
                {lesson.teacher}
              </button>
            </div>
          )}
          {showRoom && lesson.room && lesson.room !== '—' && (
            <div className="flex items-center gap-1">
              <MapPin size={11} style={{ color: 'var(--t-muted)' }} />
              <button onClick={hasRoomLink ? handleRoomClick : undefined}
                className={`text-xs transition-colors ${hasRoomLink ? 'hover:text-[var(--cyan)] cursor-pointer underline-offset-2 hover:underline tap-scale' : 'cursor-default'}`}
                style={{ color: 'var(--t-secondary)', background: 'none', border: 'none', padding: 0 }}>
                {lesson.room}
              </button>
            </div>
          )}
          {showGroupRow && (
            <div className="flex items-start gap-1">
              <Users size={11} style={{ color: 'var(--t-muted)', marginTop: 2 }} />
              <span className="text-xs leading-snug" style={{ color: 'var(--t-secondary)' }}>
                {groups.map((g, i) => (
                  <span key={g.id}>
                    {i > 0 && <span style={{ color: 'var(--t-muted)' }}>, </span>}
                    <button onClick={(e) => handleGroupClick(e, g.id, g.name)}
                      className="hover:text-[var(--cyan)] cursor-pointer underline-offset-2 hover:underline transition-colors tap-scale"
                      style={{ color: 'var(--t-secondary)', background: 'none', border: 'none', padding: 0 }}>
                      {g.name}
                    </button>
                  </span>
                ))}
              </span>
            </div>
          )}
        </div>
        {lesson.note && (
          <div className="mt-1.5 text-xs" style={{ color: 'var(--t-muted)' }}>{lesson.note}</div>
        )}
      </div>
    </div>
  )
}
