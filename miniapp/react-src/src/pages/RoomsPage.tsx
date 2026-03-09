import { useState, useCallback, useEffect } from 'react'
import { api } from '../utils/api'
import { isoToday } from '../utils/helpers'
import { IconBuilding, IconSearch } from '../components/Icons'

interface FreeRoomsResponse {
  rooms: Array<{ roomId: number; name: string; building?: string; capacity?: number }>
  by_building: Record<string, Array<{ name: string; capacity?: number }>>
  total: number
}

interface Institute {
  institute_id: number
  short_name: string
  name: string
  buildings: string[]
}

interface Props {
  isActive: boolean
  toast: (msg: string) => void
  onRoomClick: (room: string) => void
}

type OffsetChip = 'now' | '60' | '120' | '180'

export function RoomsPage({ toast, onRoomClick, isActive }: Props) {
  const [date, setDate] = useState(isoToday())
  const [time, setTime] = useState('')
  const [activeChip, setActiveChip] = useState<OffsetChip>('now')
  const [institutes, setInstitutes] = useState<Institute[]>([])
  const [allBuildings, setAllBuildings] = useState<string[]>([])
  const [selectedInstitute, setSelectedInstitute] = useState('')
  const [buildings, setBuildings] = useState<string[]>([])
  const [selectedBuilding, setSelectedBuilding] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<FreeRoomsResponse | null>(null)

  useEffect(() => {
    const now = new Date()
    setTime(now.toTimeString().slice(0, 5))
    setDate(now.toISOString().split('T')[0])

    api<{ institutes: Institute[]; all_buildings: string[] }>('/miniapp/api/institutes-with-buildings')
      .then(data => {
        setInstitutes(data.institutes ?? [])
        setAllBuildings(data.all_buildings ?? [])
        setBuildings(data.all_buildings ?? [])
      })
      .catch(() => {
        api<{ buildings: string[] }>('/miniapp/api/buildings')
          .then(d => {
            setAllBuildings(d.buildings ?? [])
            setBuildings(d.buildings ?? [])
          })
          .catch(() => {})
      })
  }, [])

  const setNow = useCallback(() => {
    const now = new Date()
    setDate(now.toISOString().split('T')[0])
    setTime(now.toTimeString().slice(0, 5))
    setActiveChip('now')
  }, [])

  const setOffset = useCallback((mins: number) => {
    const d = new Date(Date.now() + mins * 60000)
    setDate(d.toISOString().split('T')[0])
    setTime(d.toTimeString().slice(0, 5))
    setActiveChip(String(mins) as OffsetChip)
  }, [])

  const onInstituteChange = useCallback((iid: string) => {
    setSelectedInstitute(iid)
    setSelectedBuilding('')
    if (!iid) {
      setBuildings(allBuildings)
      return
    }
    const inst = institutes.find(i => i.institute_id === parseInt(iid))
    if (inst && inst.buildings.length) {
      setBuildings(inst.buildings)
    } else {
      setBuildings(allBuildings)
      if (inst) toast(`Для ${inst.name} корпуса не определены`)
    }
  }, [institutes, allBuildings, toast])

  const doSearch = useCallback(async () => {
    if (!date || !time) { toast('Укажите дату и время'); return }
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium')
    setLoading(true)
    setResult(null)
    try {
      const at = `${date}T${time}:00`
      const params = new URLSearchParams({ at, duration: '90' })
      if (selectedBuilding) params.set('building', selectedBuilding)
      const data = await api<FreeRoomsResponse>(`/miniapp/api/free-rooms?${params}`)
      setResult(data)
    } catch (e) {
      toast((e as Error).message ?? 'Ошибка')
    } finally {
      setLoading(false)
    }
  }, [date, time, selectedBuilding, toast])

  return (
    <div id="page-rooms" className={`page${isActive ? " active" : ""}`}>
      <div className="sec-head">АУДИТОРИИ</div>
      <div className="sec-subhead">Свободные прямо сейчас</div>

      {/* Date/time */}
      <div className="date-grid" style={{ marginBottom: 10 }}>
        <div>
          <div className="field-label">Дата</div>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
        </div>
        <div>
          <div className="field-label">Время</div>
          <input type="time" value={time} onChange={e => setTime(e.target.value)} />
        </div>
      </div>

      {/* Time offset chips */}
      <div className="chip-row">
        <button className={`chip${activeChip === 'now' ? ' active' : ''}`} onClick={setNow}>Сейчас</button>
        <button className={`chip${activeChip === '60' ? ' active' : ''}`} onClick={() => setOffset(60)}>+1ч</button>
        <button className={`chip${activeChip === '120' ? ' active' : ''}`} onClick={() => setOffset(120)}>+2ч</button>
        <button className={`chip${activeChip === '180' ? ' active' : ''}`} onClick={() => setOffset(180)}>+3ч</button>
      </div>

      {/* Institute selector */}
      <div style={{ marginTop: 14 }}>
        <div className="field-label">Институт</div>
        <div className="input-group" style={{ marginBottom: 8 }}>
          <IconBuilding className="input-icon" size={15} />
          <select
            value={selectedInstitute}
            onChange={e => onInstituteChange(e.target.value)}
          >
            <option value="">Все институты</option>
            {institutes.map(inst => (
              <option key={inst.institute_id} value={inst.institute_id}>
                {inst.name} ({inst.short_name})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Building selector */}
      {buildings.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div className="field-label">Корпус</div>
          <select
            value={selectedBuilding}
            onChange={e => setSelectedBuilding(e.target.value)}
          >
            <option value="">Все корпуса</option>
            {buildings.map(b => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>
      )}

      <button className="btn btn-primary" onClick={doSearch} disabled={loading}>
        {loading ? <span className="spinner" /> : <IconSearch size={15} />}
        {loading ? 'Поиск…' : 'Найти свободные'}
      </button>

      {/* Results */}
      <div style={{ marginTop: 20 }}>
        {loading && <div className="loading-center"><span className="spinner" /></div>}
        {!loading && result && (
          <FreeRoomsResult
            data={result}
            dateTime={`${date}T${time}`}
            onRoomClick={onRoomClick}
          />
        )}
      </div>
    </div>
  )
}

function FreeRoomsResult({
  data, dateTime, onRoomClick,
}: {
  data: FreeRoomsResponse
  dateTime: string
  onRoomClick: (room: string) => void
}) {
  if (!data.total) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🚫</div>
        <div className="empty-title">НЕТ АУДИТОРИЙ</div>
        <div className="empty-desc">Свободных аудиторий не найдено</div>
      </div>
    )
  }

  const label = dateTime.replace('T', ' ').slice(0, 16)

  return (
    <>
      <div className="text-muted" style={{ marginBottom: 12 }}>
        Свободно <strong style={{ color: 'var(--text-primary)' }}>{data.total}</strong> аудиторий · {label}
      </div>
      {Object.entries(data.by_building).map(([building, rooms]) => {
        if (!rooms.length) return null
        return (
          <div key={building}>
            <div className="room-group-head">
              {building}
              <span style={{ color: 'var(--text-muted)', marginLeft: 6, fontSize: 10 }}>({rooms.length})</span>
            </div>
            <div className="rooms-grid">
              {rooms.map(r => (
                <button
                  key={r.name}
                  className="room-pill"
                  onClick={() => onRoomClick(r.name)}
                  title="Посмотреть расписание аудитории"
                >
                  {r.name}
                </button>
              ))}
            </div>
          </div>
        )
      })}
    </>
  )
}
