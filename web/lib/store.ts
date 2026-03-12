/**
 * store.ts — глобальное состояние приложения.
 *
 * Хранит:
 *  - Параметры поиска расписания (mode/group/teacher/room)
 *  - Профиль пользователя (роль + группа/преподаватель)
 *  - TG-пользователь (tg_id, username, first_name, last_name, photo_url, roles)
 *  - JWT-токен (в памяти, не персистится)
 *  - Флаг готовности TG-авторизации
 *  - Избранное (favorites)
 *  - UI-настройки (theme, compact, time24h, weekFromMonday)
 *
 * Персистируется в localStorage (ключ 'ncfu-schedule'):
 *   - profile, profileComplete
 *   - tgUser (кешируем для быстрого рендера до ответа сервера)
 *   - settings (UI-настройки)
 *   - favorites
 *
 * НЕ персистируется:
 *   - authToken (безопасность)
 *   - tgAuthReady
 */

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
}

const DEFAULT_SETTINGS: UiSettings = {
  weekFromMonday: false,
  time24h:        true,
  compact:        false,
  theme:          'auto',
  accent_color:   '#5ce1e6',
}

interface ScheduleStore {
  // ── Search state ────────────────────────────────────────────────────────
  mode:        SearchMode
  groupId:     number | null
  groupName:   string | null
  teacherId:   number | null
  teacherName: string | null
  roomId:      number | null
  roomName:    string | null

  // ── User profile (расписание) ────────────────────────────────────────────
  profile:         UserProfile | null
  profileComplete: boolean

  // ── TG auth ──────────────────────────────────────────────────────────────
  tgUser:      TgUserInfo | null
  authToken:   string | null    // in-memory, НЕ персистируется
  tgAuthReady: boolean          // true когда init завершён (с TG или без)
  isAuthenticated: boolean      // true если есть валидный JWT

  // ── Избранное ────────────────────────────────────────────────────────────
  favorites: FavoriteItem[]

  // ── UI-настройки ──────────────────────────────────────────────────────────
  settings: UiSettings

  // ── Actions: search ──────────────────────────────────────────────────────
  setMode:    (m: SearchMode) => void
  setGroup:   (id: number, name: string) => void
  setTeacher: (id: number, name: string) => void
  setRoom:    (id: number, name: string) => void
  clear:      () => void

  // ── Actions: profile ─────────────────────────────────────────────────────
  setProfile:   (p: UserProfile) => void
  clearProfile: () => void

  // ── Actions: auth ────────────────────────────────────────────────────────
  setTgUser:     (u: TgUserInfo | null) => void
  setAuthToken:  (t: string | null) => void
  setTgAuthReady:(v: boolean) => void

  // ── Actions: settings ────────────────────────────────────────────────────
  updateSettings: (patch: Partial<UiSettings>) => void

  // ── Actions: favorites ───────────────────────────────────────────────────
  setFavorites: (favs: FavoriteItem[]) => void

  /**
   * applyServerSettings — вызывается после успешной TG-авторизации.
   * Мержит серверные настройки поверх локальных (сервер имеет приоритет).
   * Также восстанавливает profile если он сохранён в server settings.
   */
  applyServerSettings: (s: ServerSettings) => void
}

export const useScheduleStore = create<ScheduleStore>()(
  persist(
    (set, get) => ({
      // ── Search ──────────────────────────────────────────────────────────
      mode:        'group',
      groupId:     null,
      groupName:   null,
      teacherId:   null,
      teacherName: null,
      roomId:      null,
      roomName:    null,

      // ── Profile ─────────────────────────────────────────────────────────
      profile:         null,
      profileComplete: false,

      // ── Auth ─────────────────────────────────────────────────────────────
      tgUser:          null,
      authToken:       null,
      tgAuthReady:     false,
      isAuthenticated: false,

      // ── Favorites / Settings ─────────────────────────────────────────────
      favorites: [],
      settings:  DEFAULT_SETTINGS,

      // ── Search actions ───────────────────────────────────────────────────
      setMode:    (mode)              => set({ mode }),
      setGroup:   (groupId, groupName)   => set({ groupId, groupName }),
      setTeacher: (teacherId, teacherName) => set({ teacherId, teacherName }),
      setRoom:    (roomId, roomName)     => set({ roomId, roomName }),
      clear: () => set({
        groupId: null, groupName: null,
        teacherId: null, teacherName: null,
        roomId: null, roomName: null,
      }),

      // ── Profile actions ──────────────────────────────────────────────────
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

      // ── Auth actions ─────────────────────────────────────────────────────
      setTgUser: (tgUser) => set({ tgUser }),
      setAuthToken: (authToken) => set({
        authToken,
        isAuthenticated: !!authToken,
      }),
      setTgAuthReady: (tgAuthReady) => set({ tgAuthReady }),

      // ── Settings actions ─────────────────────────────────────────────────
      updateSettings: (patch) => set((state) => ({
        settings: { ...state.settings, ...patch },
      })),

      // ── Favorites actions ─────────────────────────────────────────────────
      setFavorites: (favorites) => set({ favorites }),

      // ── Apply server settings ─────────────────────────────────────────────
      applyServerSettings: (s) => {
        const current = get()
        const newSettings: Partial<UiSettings> = {}

        if (s.weekFromMonday  !== undefined) newSettings.weekFromMonday  = !!s.weekFromMonday
        if (s.time24h         !== undefined) newSettings.time24h         = s.time24h !== false
        if (s.compact         !== undefined) newSettings.compact         = !!s.compact
        if (s.theme           !== undefined) newSettings.theme           = String(s.theme)
        if (s.accent_color    !== undefined) newSettings.accent_color    = String(s.accent_color)

        // Восстанавливаем profile из server settings (если не установлен локально)
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
          // setProfile логика
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
      }),
    }
  )
)
