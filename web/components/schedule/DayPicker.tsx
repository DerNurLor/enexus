'use client'

import { useGestures } from '@/hooks/useGestures'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { addDays, format, startOfWeek, isSameDay } from 'date-fns'
import { ru } from 'date-fns/locale'

interface DayPickerProps {
  selected: Date
  onSelect: (d: Date) => void
}

export function DayPicker({ selected, onSelect }: DayPickerProps) {
  const weekStart = startOfWeek(selected, { weekStartsOn: 1 })
  const days       = Array.from({ length: 6 }, (_, i) => addDays(weekStart, i))
  const today      = new Date()
  const isThisWeek = isSameDay(weekStart, startOfWeek(today, { weekStartsOn: 1 }))

  const weekLabel =
    format(weekStart, 'd MMM', { locale: ru }) + ' – ' +
    format(addDays(weekStart, 5), 'd MMM', { locale: ru })

  function prevWeek() { onSelect(addDays(selected, -7)) }
  function nextWeek() { onSelect(addDays(selected, 7)) }
  function goToday()  { onSelect(today) }

  const gestures = useGestures({
    onSwipeLeft:  () => onSelect(addDays(selected, 1)),   // вперёд
    onSwipeRight: () => onSelect(addDays(selected, -1)),  // назад
    onDoubleTap:  () => onSelect(today),                  // двойной тап = сегодня
    swipeThreshold: 40,
    velocityThreshold: 0.2,
  })

  return (
    <div className="flex flex-col gap-3" {...gestures}>
      {/* Week nav */}
      <div className="flex items-center gap-1.5">
        <button onClick={prevWeek}
          className="w-9 h-9 rounded-xl flex items-center justify-center transition-colors hover:bg-white/5"
          style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <ChevronLeft size={16} style={{ color: 'var(--t-secondary)' }} />
        </button>

        {/* Week label — tap to go to today if not current week */}
        <button onClick={isThisWeek ? undefined : goToday}
          className="flex-1 h-9 rounded-xl flex items-center justify-center gap-2 text-xs font-medium transition-all"
          style={{
            background: 'var(--card)',
            border: `1px solid ${isThisWeek ? 'var(--border)' : 'color-mix(in srgb, var(--cyan) 40%, transparent)'}`,
            color: isThisWeek ? 'var(--t-secondary)' : 'var(--cyan)',
            cursor: isThisWeek ? 'default' : 'pointer',
          }}>
          {!isThisWeek && <span className="text-[10px] opacity-70">↩</span>}
          {weekLabel}
        </button>

        <button onClick={nextWeek}
          className="w-9 h-9 rounded-xl flex items-center justify-center transition-colors hover:bg-white/5"
          style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <ChevronRight size={16} style={{ color: 'var(--t-secondary)' }} />
        </button>
      </div>

      {/* Days row */}
      <div className="grid grid-cols-6 gap-1.5">
        {days.map((day) => {
          const active  = isSameDay(day, selected)
          const isToday = isSameDay(day, today)
          return (
            <button key={day.toISOString()} onClick={() => {
              onSelect(day)
              if ('vibrate' in navigator) navigator.vibrate(8)
            }}
              className="flex flex-col items-center py-2.5 rounded-xl transition-all duration-150"
              style={{
                background: active ? 'var(--cyan)' : isToday ? 'var(--cyan-dim)' : 'var(--card)',
                border: `1px solid ${active ? 'var(--cyan)' : isToday ? 'rgba(92,225,230,0.3)' : 'var(--border)'}`,
              }}>
              <span className="text-[10px] font-medium uppercase"
                style={{ color: active ? '#000' : 'var(--t-muted)' }}>
                {format(day, 'EEE', { locale: ru })}
              </span>
              <span className="text-sm font-bold mt-0.5 tabular-nums"
                style={{ color: active ? '#000' : isToday ? 'var(--cyan)' : 'var(--t-primary)' }}>
                {format(day, 'd')}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
