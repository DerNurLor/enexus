const BASE = process.env.NEXT_PUBLIC_API_URL || ''

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(`${BASE}${path}`)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  const res = await fetch(url.toString(), { next: { revalidate: 60 } })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  // Search
  search: (q: string) =>
    get<import('./types').SearchResults>('/search/', { q }),

  searchGroups: (q: string) =>
    get<{ total: number; groups: import('./types').GroupMeta[] }>('/search/groups', { q, limit: 20 }),

  searchTeachers: (q: string) =>
    get<{ total: number; teachers: import('./types').TeacherMeta[] }>('/search/teachers', { q, limit: 20 }),

  searchRooms: (q: string) =>
    get<{ total: number; rooms: import('./types').RoomMeta[] }>('/search/rooms', { q, limit: 20 }),

  // Groups
  getGroupSchedule: (groupId: number) =>
    get<import('./types').GroupSchedule>(`/groups/${groupId}/schedule`),

  getGroupDay: (groupId: number, date: string) =>
    get<import('./types').DayResponse>(`/groups/${groupId}/schedule/${date}`),

  // Schedules
  getScheduleDay: (groupId: number, day: string) =>
    get<import('./types').DayResponse>(`/schedules/group/${groupId}/day`, { day }),
}
