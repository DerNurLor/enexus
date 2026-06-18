import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { TgUserInfo, FavoriteItem, ServerSettings } from './auth'

export type SearchMode = 'group' | 'teacher' | 'room'
export type UserRole = 'student' | 'teacher'

export interface UserProfile {
  role:        UserRole
  groupId:     number | null
  groupName:   string | null
  teacherId:   number | null
  teacherName: string | null
}

export interface UiSettings {
  weekFromMonday: boolean
  time24h:        boolean
  compact:        boolean
  theme:          string   // 'auto' | 'light' | 'dark'
  accent_color:   string
  language:       string   // см. lib/i18n — общий язык интерфейса (web, miniapp, бот)
}

const DEFAULT_SETTINGS: UiSettings = {
  weekFromMonday: false,
  time24h:        true,
  compact:        false,
  theme:          'auto',
  accent_color:   '#A78BFA',
  language:       'ru',
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

  tgUser:      TgUserInfo | null
  authToken:   string | null    // in-memory, НЕ персистируется
  tgAuthReady: boolean          // true когда init завершён (с TG или без)
  isAuthenticated: boolean

  favorites: FavoriteItem[]
  settings: UiSettings

  setMode:    (m: SearchMode) => void
  setGroup:   (id: number, name: string) => void
  setTeacher: (id: number, name: string) => void
  setRoom:    (id: number, name: string) => void
  clear:      () => void

  setProfile:   (p: UserProfile) => void
  clearProfile: () => void

  setTgUser:     (u: TgUserInfo | null) => void
  setAuthToken:  (t: string | null) => void
  setTgAuthReady:(v: boolean) => void

  updateSettings: (patch: Partial<UiSettings>) => void

  groupConfirmed: boolean

  // Число новых оценок с последнего визита на страницу предметов.
  // Хранится в localStorage через partialize. Сбрасывается при открытии страницы.
  newGradesCount: number

  setFavorites: (favs: FavoriteItem[]) => void

  updateGradeSnapshot: (courses: any[]) => void
  clearNewGrades: () => void

  /**
   * applyServerSettings — мержит серверные настройки поверх локальных (сервер имеет приоритет).
   * Также восстанавливает profile если он сохранён в server settings.
   */
  applyServerSettings: (s: ServerSettings) => void
}

export const useScheduleStore = create<ScheduleStore>()(
  persist(
    (set, get) => ({
      mode:        'group',
      groupId:     null,
      groupName:   null,
      teacherId:   null,
      teacherName: null,
      roomId:      null,
      roomName:    null,

      profile:         null,
      profileComplete: false,

      tgUser:          null,
      authToken:       null,
      tgAuthReady:     false,
      isAuthenticated: false,

      favorites: [],
      settings:  DEFAULT_SETTINGS,

      groupConfirmed: false,

      newGradesCount: 0,

      setMode:    (mode)              => set({ mode }),
      setGroup:   (groupId, groupName)   => set({ groupId, groupName }),
      setTeacher: (teacherId, teacherName) => set({ teacherId, teacherName }),
      setRoom:    (roomId, roomName)     => set({ roomId, roomName }),
      clear: () => set({
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

      setTgUser: (tgUser) => set({ tgUser }),
      setAuthToken: (authToken) => set({
        authToken,
        isAuthenticated: !!authToken,
      }),
      setTgAuthReady: (tgAuthReady) => set({ tgAuthReady }),

      updateSettings: (patch) => set((state) => ({
        settings: { ...state.settings, ...patch },
      })),

      setFavorites: (favorites) => set({ favorites }),

      updateGradeSnapshot: (courses) => {
        if (typeof window === 'undefined') return
        const SNAP_KEY = 'ncfu_grade_snapshot'
        const buildSnapshot = (cs: any[]): Record<string, string> => {
          const snap: Record<string, string> = {}
          for (const course of cs) {
            for (const [typeName, lessons] of Object.entries(course.lessons || {})) {
              for (const lesson of lessons as any[]) {
                if (lesson.GradeText?.trim()) {
                  snap[`${course.Id}_${lesson.Id}`] = lesson.GradeText.trim()
                }
              }
            }
          }
          return snap
        }
        const newSnap = buildSnapshot(courses)
        let prevSnap: Record<string, string> = {}
        try {
          prevSnap = JSON.parse(localStorage.getItem(SNAP_KEY) || '{}')
        } catch { /* */ }

        let newCount = 0
        for (const key of Object.keys(newSnap)) {
          if (!prevSnap[key]) newCount++
        }

        localStorage.setItem(SNAP_KEY, JSON.stringify(newSnap))
        if (newCount > 0) set({ newGradesCount: newCount })
      },

      clearNewGrades: () => set({ newGradesCount: 0 }),

      applyServerSettings: (s) => {
        const current = get()
        const newSettings: Partial<UiSettings> = {}

        if (s.weekFromMonday  !== undefined) newSettings.weekFromMonday  = !!s.weekFromMonday
        if (s.time24h         !== undefined) newSettings.time24h         = s.time24h !== false
        if (s.compact         !== undefined) newSettings.compact         = !!s.compact
        if (s.theme           !== undefined) newSettings.theme           = String(s.theme)
        if (s.accent_color    !== undefined) newSettings.accent_color    = String(s.accent_color)
        if (s.language        !== undefined) newSettings.language        = String(s.language)

        let profileUpdate: Partial<ScheduleStore> = {}
        if (!current.profileComplete && s.profile_role) {
          const role = s.profile_role as UserRole
          const restoredProfile: UserProfile = {
            role,
            groupId:     (s.profile_group_id   as number  | null) ?? null,
            groupName:   (s.profile_group_name  as string | null) ?? null,
            teacherId:   (s.profile_teacher_id  as number  | null) ?? null,
            teacherName: (s.profile_teacher_name as string | null) ?? null,
          }
          profileUpdate = {
            profile:         restoredProfile,
            profileComplete: true,
            ...(role === 'student' && restoredProfile.groupId ? {
              mode: 'group' as SearchMode,
              groupId: restoredProfile.groupId,
              groupName: restoredProfile.groupName,
            } : {}),
            ...(role === 'teacher' && restoredProfile.teacherId ? {
              mode: 'teacher' as SearchMode,
              teacherId: restoredProfile.teacherId,
              teacherName: restoredProfile.teacherName,
            } : {}),
          }
        }

        set((state) => ({
          settings: { ...state.settings, ...newSettings },
          // groupConfirmed: confirmed если сервер явно сказал true
          // ИЛИ если есть profile_group_name но нет явного false (покрывает старые записи где флаг ещё не был записан)
          groupConfirmed: (s as any).profile_group_confirmed === true
            || ((s as any).profile_group_confirmed !== false && !!(s as any).profile_group_name),
          ...profileUpdate,
        }))
      },
    }),
    {
      name: 'ncfu-schedule',
      // Не персистируем authToken и tgAuthReady — они пересоздаются при каждом запуске
      partialize: (state) => ({
        mode:            state.mode,
        groupId:         state.groupId,
        groupName:       state.groupName,
        teacherId:       state.teacherId,
        teacherName:     state.teacherName,
        roomId:          state.roomId,
        roomName:        state.roomName,
        profile:         state.profile,
        profileComplete: state.profileComplete,
        tgUser:          state.tgUser,   // кешируем для быстрого рендера
        favorites:       state.favorites,
        settings:        state.settings,
        // groupConfirmed НЕ персистируем — всегда читается с сервера
      }),
    }
  )
)
