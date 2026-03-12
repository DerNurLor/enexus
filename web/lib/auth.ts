/**
 * auth.ts — Telegram WebApp авторизация для web-портала.
 *
 * Поток (TG Mini App):
 *   1. window.Telegram.WebApp.initData → POST /auth/telegram/login → access + refresh tokens
 *   2. GET /auth/me                    → TgUserInfo (tg_id, username, first_name, last_name, …)
 *   3. GET /miniapp/api/settings       → сохранённые настройки (profile_role, groupId, theme, …)
 *   4. GET /miniapp/api/favorites      → избранное
 *
 * Поток (обычный браузер):
 *   - Нет initData → пробуем тихий рефреш через saved refresh_token
 *   - Если рефреш провалился → анонимный режим (профиль из localStorage)
 *
 * Токены:
 *   - access  token  — только в памяти (_token)
 *   - refresh token  — localStorage (REFRESH_KEY), переживает перезагрузку
 */

const AUTH_BASE    = (process.env.NEXT_PUBLIC_API_URL || '') + '/auth'
const MINIAPP_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/miniapp'
const REFRESH_KEY  = 'ncfu_refresh_token'

// ── In-memory access token ───────────────────────────────────────────────────
let _token: string | null = null

export function getToken(): string | null { return _token }
export function setToken(t: string | null) { _token = t }
export function clearToken() {
  _token = null
  if (typeof window !== 'undefined') localStorage.removeItem(REFRESH_KEY)
}

export function getAuthHeader(): Record<string, string> {
  return _token ? { Authorization: `Bearer ${_token}` } : {}
}

// ── TG WebApp detection ──────────────────────────────────────────────────────
export function isTelegramWebApp(): boolean {
  if (typeof window === 'undefined') return false
  const tg = (window as any).Telegram?.WebApp
  return !!(tg?.initData && tg.initData.length > 0)
}

export function getTelegramInitData(): string | null {
  if (typeof window === 'undefined') return null
  return (window as any).Telegram?.WebApp?.initData || null
}

/** Данные пользователя из initDataUnsafe (доступны без сетевого запроса) */
export function getTelegramUser(): {
  id: number; first_name: string; last_name?: string; username?: string
} | null {
  if (typeof window === 'undefined') return null
  try { return (window as any).Telegram?.WebApp?.initDataUnsafe?.user || null }
  catch { return null }
}

// ── Types ────────────────────────────────────────────────────────────────────
export interface TgUserInfo {
  id:          string    // MongoDB ObjectId
  tg_id:       number
  username:    string | null
  first_name:  string
  last_name:   string | null
  photo_url:   string | null
  roles:       string[]
  is_blocked:  boolean
  last_active: string
  created_at:  string
}

export interface ServerSettings {
  weekFromMonday?:       boolean
  time24h?:              boolean
  compact?:              boolean
  notifications?:        boolean
  default_group?:        string | null
  default_teacher?:      string | null
  theme?:                string
  accent_color?:         string
  // профиль расписания — сохраняем сюда через saveSettingsToServer
  profile_role?:         string | null   // 'student' | 'teacher' | null
  profile_group_id?:     number | null
  profile_group_name?:   string | null
  profile_teacher_id?:   number | null
  profile_teacher_name?: string | null
  [key: string]: unknown
}

export interface FavoriteItem {
  type:  'group' | 'teacher' | 'room'
  id:    string
  label: string
}

export interface QuotaStatus {
  used:      number
  cap:       number
  remaining: number
  ttl_secs:  number
  ttl_hours: number
  exhausted: boolean
}

export interface AuthResult {
  token:     string
  user:      TgUserInfo
  settings:  ServerSettings
  favorites: FavoriteItem[]
}

// ── HTTP helpers ─────────────────────────────────────────────────────────────
async function _post<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`)
  return res.json()
}

async function _get<T>(url: string, token?: string): Promise<T> {
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`)
  return res.json()
}

// ── Silent refresh ───────────────────────────────────────────────────────────
async function _silentRefresh(): Promise<string | null> {
  const refresh = typeof window !== 'undefined' ? localStorage.getItem(REFRESH_KEY) : null
  if (!refresh) return null
  try {
    const data = await _post<{ access_token: string; refresh_token: string }>(
      `${AUTH_BASE}/refresh`,
      { refresh_token: refresh }
    )
    localStorage.setItem(REFRESH_KEY, data.refresh_token)
    return data.access_token
  } catch {
    localStorage.removeItem(REFRESH_KEY)
    return null
  }
}

// ── Main auth flow ───────────────────────────────────────────────────────────
/**
 * Вызывается из Providers при инициализации.
 * - В TG Mini App: initData → /auth/telegram/login → JWT
 * - В браузере: тихий рефреш через saved refresh_token
 * - Анонимно: null
 */
export async function authenticateWithTelegram(): Promise<AuthResult | null> {
  if (typeof window === 'undefined') return null

  // Инициализируем TG WebApp SDK
  const tg = (window as any).Telegram?.WebApp
  if (tg) { tg.ready?.(); tg.expand?.() }

  const initData = getTelegramInitData()
  let accessToken: string | null = null

  if (initData) {
    // ── TG Mini App: полная авторизация ────────────────────────────────────
    try {
      const loginData = await _post<{
        access_token:  string
        refresh_token: string
        totp_required: boolean
      }>(`${AUTH_BASE}/telegram/login`, { init_data: initData })

      if (!loginData.totp_required) {
        accessToken = loginData.access_token
        localStorage.setItem(REFRESH_KEY, loginData.refresh_token)
      } else {
        // TOTP — fallback к рефрешу (web не поддерживает TOTP flow)
        accessToken = await _silentRefresh()
      }
    } catch {
      accessToken = await _silentRefresh()
    }
  } else {
    // ── Обычный браузер: тихий рефреш ─────────────────────────────────────
    accessToken = await _silentRefresh()
  }

  if (!accessToken) return null

  // ── Загружаем данные параллельно ─────────────────────────────────────────
  try {
    const [userInfo, settingsData, favData] = await Promise.all([
      _get<TgUserInfo>(`${AUTH_BASE}/me`, accessToken),
      _get<{ settings: ServerSettings }>(`${MINIAPP_BASE}/api/settings`, accessToken)
        .catch(() => ({ settings: {} as ServerSettings })),
      _get<{ favorites: FavoriteItem[] }>(`${MINIAPP_BASE}/api/favorites`, accessToken)
        .catch(() => ({ favorites: [] as FavoriteItem[] })),
    ])

    return {
      token:     accessToken,
      user:      userInfo,
      settings:  settingsData.settings  ?? {},
      favorites: favData.favorites ?? [],
    }
  } catch {
    // me загрузить не удалось — нет смысла в токене
    return null
  }
}

// ── Server sync helpers ──────────────────────────────────────────────────────

export async function saveSettingsToServer(settings: Partial<ServerSettings>): Promise<void> {
  if (!_token) return
  try {
    await fetch(`${MINIAPP_BASE}/api/settings`, {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${_token}` },
      body:    JSON.stringify(settings),
    })
  } catch { /* не блокируем UI */ }
}

export async function loadSettingsFromServer(): Promise<ServerSettings | null> {
  if (!_token) return null
  try {
    const data = await _get<{ settings: ServerSettings }>(`${MINIAPP_BASE}/api/settings`, _token)
    return data.settings || null
  } catch { return null }
}

export async function fetchQuota(): Promise<QuotaStatus | null> {
  if (!_token) return null
  try { return await _get<QuotaStatus>(`${MINIAPP_BASE}/api/profile/limits`, _token) }
  catch { return null }
}

export async function addFavorite(item: FavoriteItem): Promise<FavoriteItem[]> {
  if (!_token) return []
  try {
    const data = await _post<{ favorites: FavoriteItem[] }>(`${MINIAPP_BASE}/api/favorites`, item)
    return data.favorites
  } catch { return [] }
}

export async function removeFavorite(type: string, id: string): Promise<FavoriteItem[]> {
  if (!_token) return []
  try {
    const res = await fetch(`${MINIAPP_BASE}/api/favorites/${encodeURIComponent(type)}:${encodeURIComponent(id)}`, {
      method:  'DELETE',
      headers: { Authorization: `Bearer ${_token}` },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.favorites ?? []
  } catch { return [] }
}
