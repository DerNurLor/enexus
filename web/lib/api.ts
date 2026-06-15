import { getAuthHeader } from './auth'

const BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/api'

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(
    `${BASE}${path}`,
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
  )
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  const res = await fetch(url.toString(), { next: { revalidate: 60 } })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

async function authedGet<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_URL || ''
  const url = new URL(
    `${base}${path}`,
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
  )
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  const res = await fetch(url.toString(), {
    headers: getAuthHeader(),
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  searchGroups: (q: string) =>
    get<{ total: number; groups: import('./types').GroupMeta[] }>('/search/groups', { q, limit: 20 }),

  searchTeachers: (q: string) =>
    get<{ total: number; teachers: import('./types').TeacherMeta[] }>('/search/teachers', { q, limit: 20 }),

  searchRooms: (q: string) =>
    get<{ total: number; rooms: import('./types').RoomMeta[] }>('/search/rooms', { q, limit: 20 }),

  getGroupDay: (groupId: number, date: string) =>
    get<import('./types').DayResponse>(`/schedules/group/${groupId}/day`, { day: date }),

  getTeacherDay: (teacherId: number, date: string) =>
    get<import('./types').DayResponse>(`/schedules/teacher/${teacherId}/day`, { day: date }),

  getRoomDay: (roomId: number, date: string) =>
    get<import('./types').DayResponse>(`/schedules/room/${roomId}/day`, { day: date }),

  getGroupWeek: (groupId: number, week: number) =>
    get<import('./types').WeekResponse>(`/schedules/group/${groupId}/week`, { week }),

  getTeacherWeek: (teacherId: number, week: number) =>
    get<import('./types').WeekResponse>(`/teachers/${teacherId}/week`, { week }),

  getRoomWeek: (roomId: number, week: number) =>
    get<import('./types').WeekResponse>(`/rooms/${roomId}/week`, { week }),

  getFreeRooms: (at: string, duration?: number, building?: string, instituteId?: number) => {
    const params: Record<string, string | number> = { at, duration: duration ?? 90 }
    if (building)    params.building     = building
    if (instituteId) params.institute_id = instituteId
    return get<import('./types').FreeRoomsResponse>('/rooms/free', params)
  },

  getInstitutesWithBuildings: () =>
    get<{ institutes: import('./types').InstituteMeta[]; all_buildings: string[] }>('/institutes/with-buildings'),

  getBuildings: () =>
    get<{ buildings: string[] }>('/rooms/buildings-list'),

  getTeacher: (teacherId: number) =>
    get<import('./types').TeacherFull>(`/teachers/${teacherId}`),

  getTeacherStats: (teacherId: number) =>
    get<import('./types').TeacherStats>(`/teachers/${teacherId}/stats`),

  getTeacherTodayRooms: (teacherId: number) =>
    get<{ date: string; rooms: import('./types').TodayRoom[] }>(`/teachers/${teacherId}/today-rooms`),

  getTeacherGroups: (teacherId: number) =>
    get<{ teacher_id: number; full_name: string; group_count: number; groups: import('./types').GroupMeta[] }>(`/search/teacher-groups`, { teacher_id: teacherId }),

  getQuotaStatus: () =>
    authedGet<import('./auth').QuotaStatus>('/miniapp/api/profile/limits'),
}
