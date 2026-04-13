'use client'
/**
 * UpcomingLessonWidget.tsx
 *
 * Виджет «Ближайшее занятие без оценки» для главной страницы расписания.
 * Показывается только авторизованным студентам у которых подключён eCampus.
 *
 * Размещение: web/components/ecampus/UpcomingLessonWidget.tsx
 * Использование: импортировать на schedule page и рендерить над расписанием.
 */
import { useQuery } from '@tanstack/react-query'
import { useScheduleStore } from '@/lib/store'
import { BookOpen, ChevronRight, X } from 'lucide-react'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/api'

async function fetchWidget(daysAhead: number): Promise<any> {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  if (!token) return null
  const res = await fetch(`${API_BASE}/overview/ecampus-widget?days_ahead=${daysAhead}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return null
  return res.json()
}

const TYPE_COLORS: Record<string, string> = {
  'Экзамен':       '#f87171',
  'Зачёт':         '#fbbf24',
  'Диф. зачёт':    '#fbbf24',
  'Курсовая':      '#a78bfa',
  'Лекция':        '#60a5fa',
  'Практика':      '#34d399',
  'Лаб.':          '#4ade80',
}

function lessonTypeColor(lt: string): string {
  return TYPE_COLORS[lt] || '#94a3b8'
}

export function UpcomingLessonWidget() {
  const { authToken, profile } = useScheduleStore()
  const [dismissed, setDismissed] = useState(false)
  const router = useRouter()

  // Только для авторизованных студентов
  const isStudent = profile?.role === 'student' && profile?.groupId

  const { data } = useQuery({
    queryKey: ['ecampus-widget'],
    queryFn: () => fetchWidget(2),
    enabled: !!authToken && !!isStudent && !dismissed,
    staleTime: 5 * 60_000,
    refetchInterval: 15 * 60_000,
  })

  if (dismissed || !authToken || !isStudent) return null
  if (!data?.items?.length) return null

  const items: any[] = data.items.slice(0, 3)

  return (
    <div className="mb-4 rounded-2xl overflow-hidden animate-fade-up"
      style={{ border: '1px solid color-mix(in srgb, var(--accent) 25%, transparent)', background: 'color-mix(in srgb, var(--accent) 5%, transparent)' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5"
        style={{ borderBottom: '1px solid color-mix(in srgb, var(--accent) 12%, transparent)' }}>
        <div className="flex items-center gap-2">
          <BookOpen size={13} style={{ color: 'var(--accent)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--accent)' }}>
            Занятия без оценок
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
            style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
            {items.length}
          </span>
        </div>
        <button onClick={() => setDismissed(true)}
          className="p-1 rounded-lg hover:bg-white/5" style={{ color: 'var(--t-muted)' }}>
          <X size={12} />
        </button>
      </div>

      {/* Items */}
      <div className="divide-y" style={{ borderColor: 'color-mix(in srgb, var(--accent) 8%, transparent)' }}>
        {items.map((item, i) => {
          const isToday = item.date === new Date().toISOString().slice(0, 10)
          const dt = new Date(item.date)
          const dateLabel = isToday
            ? 'Сегодня'
            : dt.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' })

          return (
            <button
              key={i}
              onClick={() => router.push(
                `/schedule?mode=group&id=${item.group_id}&name=${encodeURIComponent(item.group_name || '')}&date=${item.date}`
              )}
              className="w-full text-left flex items-center gap-3 px-4 py-2.5 hover:bg-white/3 group"
            >
              {/* Date / Time */}
              <div className="shrink-0 text-center w-14">
                <div className="text-[10px] font-semibold" style={{ color: 'var(--accent)' }}>
                  {dateLabel}
                </div>
                <div className="text-[11px] font-mono" style={{ color: 'var(--t-muted)' }}>
                  {item.timeStart}
                </div>
              </div>

              {/* Subject */}
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium truncate" style={{ color: 'var(--t-primary)' }}>
                  {item.subject}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                  {item.lessonType && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold shrink-0"
                      style={{
                        background: `${lessonTypeColor(item.lessonType)}15`,
                        color: lessonTypeColor(item.lessonType),
                      }}>
                      {item.lessonType}
                    </span>
                  )}
                  {item.room && (
                    <span className="text-[10px] truncate" style={{ color: 'var(--t-muted)' }}>
                      {item.room}
                    </span>
                  )}
                  <span className="text-[9px] ml-auto shrink-0" style={{ color: '#fbbf24' }}>
                    оценок нет
                  </span>
                </div>
              </div>

              <ChevronRight size={12} className="shrink-0 opacity-0 group-hover:opacity-100"
                style={{ color: 'var(--accent)' }} />
            </button>
          )
        })}
      </div>

      {/* Footer link to ecampus */}
      <div className="px-4 py-2 flex justify-end">
        <button onClick={() => router.push('/ecampus')}
          className="text-[10px] hover:underline" style={{ color: 'var(--accent)' }}>
          Все предметы →
        </button>
      </div>
    </div>
  )
}
