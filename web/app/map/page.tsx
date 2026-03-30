'use client'

import { useState, useEffect } from 'react'
import { useQuery }          from '@tanstack/react-query'
import { PageHeader }        from '@/components/layout/PageHeader'
import { useScheduleStore }  from '@/lib/store'
import { api }               from '@/lib/api'
import { MapPin, DoorOpen, Clock, ChevronRight } from 'lucide-react'
import { useRouter }         from 'next/navigation'

const BUILDINGS = [
  { id: '1',  label: 'Корпус 1',   desc: 'ул. Пушкина, 1',       color: '#5ce1e6' },
  { id: '2',  label: 'Корпус 2',   desc: 'ул. Пушкина, 1',       color: '#a78bfa' },
  { id: '8',  label: 'Корпус 8',   desc: 'пр. Кулакова, 2',      color: '#4ade80' },
  { id: '11', label: 'Корпус 11',  desc: 'ул. Тухачевского, 4',  color: '#fb923c' },
  { id: 'Б',  label: 'Библиотека', desc: 'ул. Пушкина, 1',       color: '#f472b6' },
]

function isoNow() {
  const d = new Date()
  return `${d.toISOString().split('T')[0]}T${d.toTimeString().slice(0, 5)}`
}

export default function MapPage() {
  const router = useRouter()
  const { setRoom, setMode } = useScheduleStore()
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null)
  const [at, setAt] = useState(isoNow())

  useEffect(() => {
    const id = setInterval(() => setAt(isoNow()), 60_000)
    return () => clearInterval(id)
  }, [])

  const { data: freeRoomsData, isLoading } = useQuery({
    queryKey: ['free-rooms-map', at.slice(0, 16), selectedBuilding],
    queryFn:  () => api.getFreeRooms(at, 90, selectedBuilding || undefined),
    staleTime: 60_000,
    refetchInterval: 120_000,
  })

  // by_building: Record<string, Array<{ name: string; capacity?: number; room_id?: number }>>
  const byBuilding = freeRoomsData?.by_building ?? {}
  const totalFree  = freeRoomsData?.total ?? 0

  function openRoomSchedule(roomId: number | undefined, roomName: string) {
    if (!roomId) return
    setMode('room')
    setRoom(roomId, roomName)
    router.push('/schedule')
  }

  return (
    <div className="px-4 lg:px-0">
      <PageHeader title="Карта кампуса" />

      <div className="flex items-center justify-between mb-4 px-4 py-3 rounded-xl"
        style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <Clock size={14} style={{ color: 'var(--cyan)' }} />
          <span className="text-sm font-mono" style={{ color: 'var(--t-primary)' }}>
            {at.split('T')[1]}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {isLoading
            ? <span className="text-xs" style={{ color: 'var(--t-muted)' }}>Загрузка...</span>
            : <>
                <span className="text-sm font-bold" style={{ color: '#4ade80' }}>{totalFree}</span>
                <span className="text-xs" style={{ color: 'var(--t-muted)' }}>свободных аудиторий</span>
              </>
          }
        </div>
      </div>

      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        <button
          onClick={() => setSelectedBuilding(null)}
          className="shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors"
          style={{
            background: !selectedBuilding ? 'var(--cyan)' : 'var(--card)',
            color:      !selectedBuilding ? '#000' : 'var(--t-secondary)',
            border:     '1px solid var(--border)',
          }}
        >
          Все
        </button>
        {BUILDINGS.map(b => {
          const rooms = byBuilding[b.id] ?? []
          const isActive = selectedBuilding === b.id
          return (
            <button
              key={b.id}
              onClick={() => setSelectedBuilding(isActive ? null : b.id)}
              className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors"
              style={{
                background: isActive ? b.color + '22' : 'var(--card)',
                color:      isActive ? b.color : 'var(--t-secondary)',
                border:     `1px solid ${isActive ? b.color + '55' : 'var(--border)'}`,
              }}
            >
              {b.label}
              {rooms.length > 0 && (
                <span className="text-[10px] px-1 rounded-full"
                  style={{ background: b.color + '33', color: b.color }}>
                  {rooms.length}
                </span>
              )}
            </button>
          )
        })}
      </div>

      <div className="flex flex-col gap-3">
        {BUILDINGS
          .filter(b => !selectedBuilding || b.id === selectedBuilding)
          .map(building => {
            const rooms = byBuilding[building.id] ?? []
            return (
              <div key={building.id} className="card overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3"
                  style={{
                    borderBottom: rooms.length > 0 ? '1px solid var(--border)' : 'none',
                    borderLeft:   `3px solid ${building.color}`,
                  }}>
                  <div>
                    <p className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>
                      {building.label}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--t-muted)' }}>
                      {building.desc}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {isLoading
                      ? <div className="w-8 h-5 rounded animate-pulse" style={{ background: 'var(--border)' }} />
                      : rooms.length > 0
                        ? <>
                            <span className="text-sm font-bold" style={{ color: '#4ade80' }}>{rooms.length}</span>
                            <DoorOpen size={14} style={{ color: '#4ade80' }} />
                          </>
                        : <span className="text-xs" style={{ color: 'var(--t-muted)' }}>нет свободных</span>
                    }
                  </div>
                </div>

                {rooms.length > 0 && (
                  <div>
                    {rooms.slice(0, 6).map((room, i) => (
                      <button
                        key={`${room.name}-${i}`}
                        onClick={() => openRoomSchedule(room.room_id, room.name)}
                        disabled={!room.room_id}
                        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/3 transition-colors text-left disabled:opacity-60"
                        style={{ borderTop: i > 0 ? '1px solid var(--border)' : 'none' }}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <MapPin size={11} style={{ color: 'var(--t-muted)', flexShrink: 0 }} />
                          <span className="text-sm truncate" style={{ color: 'var(--t-primary)' }}>
                            {room.name}
                          </span>
                        </div>
                        {room.room_id && (
                          <ChevronRight size={12} style={{ color: 'var(--t-muted)', flexShrink: 0 }} />
                        )}
                      </button>
                    ))}
                    {rooms.length > 6 && (
                      <div className="px-4 py-2 text-center"
                        style={{ borderTop: '1px solid var(--border)' }}>
                        <span className="text-xs" style={{ color: 'var(--t-muted)' }}>
                          + ещё {rooms.length - 6} аудиторий
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
      </div>

      <div className="mt-4 text-center">
        <button
          onClick={() => router.push('/rooms')}
          className="text-xs px-4 py-2 rounded-xl"
          style={{ color: 'var(--cyan)', border: '1px solid rgba(92,225,230,0.3)' }}
        >
          Расширенный поиск аудиторий →
        </button>
      </div>
    </div>
  )
}
