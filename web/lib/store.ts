import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type SearchMode = 'group' | 'teacher' | 'room'
export type UserRole = 'student' | 'teacher'

export interface UserProfile {
  role:        UserRole
  groupId:     number | null
  groupName:   string | null
  teacherId:   number | null
  teacherName: string | null
}

interface ScheduleStore {
  mode:        SearchMode
  groupId:     number | null
  groupName:   string | null
  teacherId:   number | null
  teacherName: string | null
  roomId:      number | null
  roomName:    string | null

  profile:         UserProfile | null
  profileComplete: boolean

  setMode:      (m: SearchMode) => void
  setGroup:     (id: number, name: string) => void
  setTeacher:   (id: number, name: string) => void
  setRoom:      (id: number, name: string) => void
  clear:        () => void
  setProfile:   (p: UserProfile) => void
  clearProfile: () => void
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

      profile:         null,
      profileComplete: false,

      setMode:    (mode) => set({ mode }),
      setGroup:   (groupId, groupName) => set({ groupId, groupName }),
      setTeacher: (teacherId, teacherName) => set({ teacherId, teacherName }),
      setRoom:    (roomId, roomName) => set({ roomId, roomName }),
      clear:      () => set({
        groupId: null, groupName: null,
        teacherId: null, teacherName: null,
        roomId: null, roomName: null,
      }),

      setProfile: (profile) => set({
        profile,
        profileComplete: true,
        ...(profile.role === 'student' && profile.groupId ? {
          mode: 'group' as SearchMode,
          groupId: profile.groupId,
          groupName: profile.groupName,
        } : {}),
        ...(profile.role === 'teacher' && profile.teacherId ? {
          mode: 'teacher' as SearchMode,
          teacherId: profile.teacherId,
          teacherName: profile.teacherName,
        } : {}),
      }),
      clearProfile: () => set({ profile: null, profileComplete: false }),
    }),
    { name: 'ncfu-schedule' }
  )
)
