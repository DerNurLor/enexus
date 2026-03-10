import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type SearchMode = 'group' | 'teacher' | 'room'

interface ScheduleStore {
  mode:       SearchMode
  groupId:    number | null
  groupName:  string | null
  teacherId:  number | null
  teacherName: string | null
  roomId:     number | null
  roomName:   string | null

  setMode:    (m: SearchMode) => void
  setGroup:   (id: number, name: string) => void
  setTeacher: (id: number, name: string) => void
  setRoom:    (id: number, name: string) => void
  clear:      () => void
}

export const useScheduleStore = create<ScheduleStore>()(
  persist(
    (set) => ({
      mode:        'group',
      groupId:     null,
      groupName:   null,
      teacherId:   null,
      teacherName: null,
      roomId:      null,
      roomName:    null,

      setMode:    (mode) => set({ mode }),
      setGroup:   (groupId, groupName) => set({ groupId, groupName }),
      setTeacher: (teacherId, teacherName) => set({ teacherId, teacherName }),
      setRoom:    (roomId, roomName) => set({ roomId, roomName }),
      clear:      () => set({ groupId: null, groupName: null, teacherId: null, teacherName: null, roomId: null, roomName: null }),
    }),
    { name: 'ncfu-schedule' }
  )
)
