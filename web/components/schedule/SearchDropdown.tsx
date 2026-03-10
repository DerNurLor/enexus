'use client'

import { useScheduleStore } from '@/lib/store'
import type { GroupMeta, TeacherMeta, RoomMeta } from '@/lib/types'

type SearchMode = 'group' | 'teacher' | 'room'

interface Props {
  mode: SearchMode
  data: { groups?: GroupMeta[]; teachers?: TeacherMeta[]; rooms?: RoomMeta[]; total?: number } | null
  onClose: () => void
}

export function SearchDropdown({ mode, data, onClose }: Props) {
  const { setGroup, setTeacher, setRoom } = useScheduleStore()

  if (!data) return null

  const groups   = data.groups   || []
  const teachers = data.teachers || []
  const rooms    = data.rooms    || []

  const isEmpty =
    (mode === 'group'   && groups.length === 0) ||
    (mode === 'teacher' && teachers.length === 0) ||
    (mode === 'room'    && rooms.length === 0)

  return (
    <div
      className="absolute top-full left-0 right-0 mt-1 rounded-2xl overflow-hidden z-50"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        maxHeight: 320,
        overflowY: 'auto',
      }}
    >
      {isEmpty ? (
        <div className="px-4 py-6 text-center text-xs" style={{ color: 'var(--t-muted)' }}>
          Ничего не найдено
        </div>
      ) : (
        <ul>
          {mode === 'group' && groups.map((g) => (
            <li key={g.group_id}>
              <button
                className="w-full text-left px-4 py-3 transition-colors hover:bg-white/5 flex items-center justify-between gap-3"
                onClick={() => { setGroup(g.group_id, g.name); onClose() }}
              >
                <div>
                  <div className="text-sm font-medium" style={{ color: 'var(--t-primary)' }}>{g.name}</div>
                  <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--t-muted)' }}>
                    {g.speciality_name} · {g.course} курс
                  </div>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded flex-shrink-0"
                  style={{ background: 'var(--cyan-dim)', color: 'var(--cyan)' }}>
                  {g.academic_year}
                </span>
              </button>
            </li>
          ))}

          {mode === 'teacher' && teachers.map((t) => (
            <li key={t.teacher_id}>
              <button
                className="w-full text-left px-4 py-3 transition-colors hover:bg-white/5"
                onClick={() => { setTeacher(t.teacher_id, t.full_name); onClose() }}
              >
                <div className="text-sm font-medium" style={{ color: 'var(--t-primary)' }}>{t.full_name}</div>
                {t.subjects.length > 0 && (
                  <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--t-muted)' }}>
                    {t.subjects.slice(0, 3).join(', ')}
                  </div>
                )}
              </button>
            </li>
          ))}

          {mode === 'room' && rooms.map((r) => (
            <li key={r.room_id}>
              <button
                className="w-full text-left px-4 py-3 transition-colors hover:bg-white/5 flex items-center gap-3"
                onClick={() => { setRoom(r.room_id, r.name); onClose() }}
              >
                <div>
                  <div className="text-sm font-medium" style={{ color: 'var(--t-primary)' }}>{r.name}</div>
                  {r.building && (
                    <div className="text-xs mt-0.5" style={{ color: 'var(--t-muted)' }}>{r.building}</div>
                  )}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
