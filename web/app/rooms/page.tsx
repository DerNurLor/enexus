'use client'

import { useState, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Building2, Search, Clock, DoorOpen } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { useScheduleStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { FreeRoomsResponse, InstituteMeta } from '@/lib/types'

type Chip = 'now' | '60' | '120' | '180'

function isoNow(offsetMs = 0) {
  const d = new Date(Date.now() + offsetMs)
  return {
    date: d.toISOString().split('T')[0],
    time: d.toTimeString().slice(0, 5),
  }
}

export default function RoomsPage() {
  const { setRoom, setMode } = useScheduleStore()

  const [date, setDate]                 = useState(isoNow().date)
  const [time, setTime]                 = useState(isoNow().time)
  const [activeChip, setActiveChip]     = useState<Chip>('now')
  const [selectedBuilding, setBuilding] = useState('')
  const [institutes, setInstitutes]     = useState<InstituteMeta[]>([])
  const [allBuildings, setAllBuildings] = useState<string[]>([])
  const [buildings, setBuildings]       = useState<string[]>([])
  const [selectedInst, setSelectedInst] = useState('')
  const [triggered, setTriggered]       = useState(false)

  // Load institutes & buildings
  useEffect(() => {
    api.getInstitutesWithBuildings()
      .then(d => {
        setInstitutes(d.institutes ?? [])
        setAllBuildings(d.all_buildings ?? [])
        setBuildings(d.all_buildings ?? [])
      })
      .catch(() => {
        api.getBuildings()
          .then(d => {
            setAllBuildings(d.buildings ?? [])
            setBuildings(d.buildings ?? [])
          })
          .catch(() => {})
      })
  }, [])

  function setChip(chip: Chip) {
    const offset = chip === 'now' ? 0 : parseInt(chip) * 60000
    const { date: d, time: t } = isoNow(offset)
    setDate(d); setTime(t); setActiveChip(chip)
  }

  function onInstChange(iid: string) {
    setSelectedInst(iid)
    setBuilding('')
    if (!iid) { setBuildings(allBuildings); return }
    const inst = institutes.find(i => i.institute_id === parseInt(iid))
    if (inst?.buildings.length) setBuildings(inst.buildings)
    else setBuildings(allBuildings)
  }

  const atParam = `${date}T${time}:00`

  const { data, isLoading, isError, refetch } = useQuery<FreeRoomsResponse>({
    queryKey: ['freeRooms', atParam, selectedBuilding, selectedInst],
    queryFn:  () => api.getFreeRooms(
      atParam,
      90,
      selectedBuilding || undefined,
      selectedInst ? parseInt(selectedInst) : undefined,
    ),
    enabled:  triggered,
    retry: 1,
  })

  const doSearch = useCallback(() => {
    setTriggered(true)
    if (triggered) refetch()
  }, [triggered, refetch])

  function handleRoomClick(roomName: string, roomId?: number) {
    if (roomId) {
      setMode('room')
      setRoom(roomId, roomName)
      window.location.href = '/schedule'
    }
  }

  const CHIPS: [Chip, string][] = [['now', 'Сейчас'], ['60', '+1ч'], ['120', '+2ч'], ['180', '+3ч']]

  return (
    <div className="px-4 lg:px-0">
      <PageHeader title="Аудитории" />

      <p className="text-sm mb-5" style={{ color: 'var(--t-secondary)' }}>
        Свободные аудитории на выбранное время
      </p>

      {/* Date / Time */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label className="text-xs mb-1 block" style={{ color: 'var(--t-muted)' }}>Дата</label>
          <input
            type="date"
            value={date}
            onChange={e => { setDate(e.target.value); setActiveChip('' as Chip) }}
            className="input-search"
            style={{ colorScheme: 'dark' }}
          />
        </div>
        <div>
          <label className="text-xs mb-1 block" style={{ color: 'var(--t-muted)' }}>Время</label>
          <input
            type="time"
            value={time}
            onChange={e => { setTime(e.target.value); setActiveChip('' as Chip) }}
            className="input-search"
            style={{ colorScheme: 'dark' }}
          />
        </div>
      </div>

      {/* Quick time chips */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {CHIPS.map(([chip, label]) => (
          <button
            key={chip}
            onClick={() => setChip(chip)}
            className="pill"
            style={activeChip === chip
              ? { background: 'var(--cyan)', color: '#000' }
              : { background: 'var(--card)', color: 'var(--t-secondary)', border: '1px solid var(--border)' }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Institute selector */}
      {institutes.length > 0 && (
        <div className="mb-3">
          <label className="text-xs mb-1 block" style={{ color: 'var(--t-muted)' }}>Институт</label>
          <div className="relative">
            <Building2 size={14} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: 'var(--t-muted)' }} />
            <select
              value={selectedInst}
              onChange={e => onInstChange(e.target.value)}
              className="input-search pl-9 appearance-none cursor-pointer"
              style={{ colorScheme: 'dark' }}
            >
              <option value="">Все институты</option>
              {institutes.map(i => (
                <option key={i.institute_id} value={i.institute_id}>
                  {i.name} ({i.short_name})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Building selector */}
      {buildings.length > 0 && (
        <div className="mb-5">
          <label className="text-xs mb-1 block" style={{ color: 'var(--t-muted)' }}>Корпус</label>
          <select
            value={selectedBuilding}
            onChange={e => setBuilding(e.target.value)}
            className="input-search appearance-none cursor-pointer"
            style={{ colorScheme: 'dark' }}
          >
            <option value="">Все корпуса</option>
            {buildings.map(b => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>
      )}

      <button
        onClick={doSearch}
        disabled={isLoading}
        className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black transition-opacity hover:opacity-90 mb-6"
        style={{ background: isLoading ? 'rgba(92,225,230,0.5)' : 'var(--cyan)' }}
      >
        {isLoading
          ? <span className="w-4 h-4 border-2 border-black/40 border-t-black rounded-full animate-spin" />
          : <Search size={16} />}
        {isLoading ? 'Поиск…' : 'Найти свободные'}
      </button>

      {/* Results */}
      {isError && (
        <p className="text-center text-sm py-8" style={{ color: 'var(--t-muted)' }}>
          Ошибка загрузки. Попробуйте ещё раз.
        </p>
      )}

      {!isLoading && data && (
        <FreeRoomsResult
          data={data}
          dateTime={atParam}
          onRoomClick={handleRoomClick}
        />
      )}

      {!triggered && !isLoading && (
        <div className="flex flex-col items-center py-14 gap-3">
          <DoorOpen size={40} style={{ color: 'var(--t-muted)' }} />
          <span className="text-sm text-center" style={{ color: 'var(--t-muted)' }}>
            Выберите время и нажмите «Найти свободные»
          </span>
        </div>
      )}
    </div>
  )
}

function FreeRoomsResult({
  data,
  dateTime,
  onRoomClick,
}: {
  data: FreeRoomsResponse
  dateTime: string
  onRoomClick: (name: string, id?: number) => void
}) {
  if (!data.total) {
    return (
      <div className="flex flex-col items-center py-14 gap-3">
        <DoorOpen size={40} style={{ color: 'var(--t-muted)' }} />
        <p className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>Нет свободных аудиторий</p>
        <p className="text-xs" style={{ color: 'var(--t-muted)' }}>Попробуйте другое время или корпус</p>
      </div>
    )
  }

  const label = dateTime.replace('T', ' ').slice(0, 16)

  return (
    <div className="animate-fade-up">
      <p className="text-xs mb-4" style={{ color: 'var(--t-muted)' }}>
        Свободно <strong style={{ color: 'var(--t-primary)' }}>{data.total}</strong> аудиторий · {label}
      </p>

      {Object.entries(data.by_building).map(([building, rooms]) => {
        if (!rooms.length) return null
        return (
          <div key={building} className="mb-5">
            <div className="flex items-center gap-2 mb-2">
              <Building2 size={13} style={{ color: 'var(--cyan)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t-secondary)' }}>
                {building}
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded"
                style={{ background: 'var(--cyan-dim)', color: 'var(--cyan)' }}>
                {rooms.length}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {rooms.map(r => (
                <button
                  key={r.name}
                  onClick={() => onRoomClick(r.name, r.room_id)}
                  className="px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 hover:scale-105"
                  style={{
                    background: 'var(--card)',
                    border: '1px solid var(--border)',
                    color: 'var(--cyan)',
                  }}
                >
                  {r.name}
                </button>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
