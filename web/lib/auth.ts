/**
 * auth.ts — Telegram авторизация для web-портала.
 *
 * Два потока авторизации:
 *
 * 1. Telegram Mini App (внутри Telegram):
 *    window.Telegram.WebApp.initData → POST /auth/telegram/login → JWT
 *
 * 2. Обычный браузер (Telegram Login Widget):
 *    Пользователь нажимает кнопку → Telegram popup → callback с данными
 *    → POST /auth/telegram/widget → JWT
 *
 * 3. Тихий рефреш (повторный визит):
 *    localStorage(refresh_token) → POST /auth/refresh → новый access token
 *
 * Безопасность:
 *  - access token  — только в памяти (не переживает reload)
 *  - refresh token — localStorage (переживает reload, используется для тихого входа)
 *  - Вся проверка подписи — на сервере
 */

const AUTH_BASE    = (process.env.NEXT_PUBLIC_API_URL || '') + '/auth'
const MINIAPP_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/miniapp'
const REFRESH_KEY  = 'ncfu_refresh_token'

// ── In-memory access token ────────────────────────────────────────────────────
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

// ── Telegram detection ────────────────────────────────────────────────────────
export function isTelegramWebApp(): boolean {
  if (typeof window === 'undefined') return false
  const tg = (window as any).Telegram?.WebApp
  return !!(tg?.initData && tg.initData.length > 0)
}
export function getTelegramInitData(): string | null {
  if (typeof window === 'undefined') return null
  return (window as any).Telegram?.WebApp?.initData || null
}
export function getTelegramUser() {
  if (typeof window === 'undefined') return null
  try { return (window as any).Telegram?.WebApp?.initDataUnsafe?.user || null }
  catch { return null }
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface TgUserInfo {
  id:          string
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

export interface TelegramWidgetData {
  id:         number
  first_name: string
  last_name?: string
  username?:  string
  photo_url?: string
  auth_date:  number
  hash:       string
}

export interface ServerSettings {
  weekFromMonday?:   boolean
  time24h?:          boolean
  compact?:          boolean
  notifications?:    boolean
  default_group?:    string | null
  default_teacher?:  string | null
  theme?:            string
  accent_color?:     string
}

export interface FavoriteItem {
  type:  'group' | 'teacher'
  id:    string | number
  name:  string
}

// ── Auth flows ────────────────────────────────────────────────────────────────

/**
 * Авторизация через Telegram Mini App initData.
 * Используется когда приложение открыто внутри Telegram.
 */
export async function loginWithInitData(initData: string): Promise<{
  access_token: string
  refresh_token: string
}> {
  const res = await fetch(`${AUTH_BASE}/telegram/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: initData }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Auth error ${res.status}`)
  }
  return res.json()
}

/**
 * Авторизация через Telegram Login Widget (обычный браузер).
 * Данные приходят из callback виджета и отправляются на сервер для проверки.
 */
export async function loginWithWidget(data: TelegramWidgetData): Promise<{
  access_token: string
  refresh_token: string
}> {
  const res = await fetch(`${AUTH_BASE}/telegram/widget`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Widget auth error ${res.status}`)
  }
  return res.json()
}

/** Тихий рефреш — пробуем обновить токены по saved refresh_token */
async function _silentRefresh(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  const refresh = localStorage.getItem(REFRESH_KEY)
  if (!refresh) return null

  try {
    const res = await fetch(`${AUTH_BASE}/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) {
      localStorage.removeItem(REFRESH_KEY)
      return null
    }
    const { access_token, refresh_token } = await res.json()
    _token = access_token
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token)
    return access_token
  } catch {
    localStorage.removeItem(REFRESH_KEY)
    return null
  }
}

// ── Fetch user info ───────────────────────────────────────────────────────────

export async function fetchMe(): Promise<TgUserInfo | null> {
  if (!_token) return null
  try {
    const res = await fetch(`${AUTH_BASE}/me`, {
      headers: getAuthHeader(),
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function fetchSettings(): Promise<ServerSettings> {
  const res = await fetch(`${MINIAPP_BASE}/api/settings`, {
    headers: getAuthHeader(),
  })
  if (!res.ok) return {}
  return res.json()
}

export async function fetchFavorites(): Promise<FavoriteItem[]> {
  const res = await fetch(`${MINIAPP_BASE}/api/favorites`, {
    headers: getAuthHeader(),
  })
  if (!res.ok) return []
  return res.json()
}

export async function saveSettingsToServer(settings: ServerSettings): Promise<void> {
  if (!_token) return
  await fetch(`${MINIAPP_BASE}/api/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
    body: JSON.stringify(settings),
  })
}

export async function fetchQuota(): Promise<{
  used: number; limit: number; reset_in: number
} | null> {
  if (!_token) return null
  try {
    const res = await fetch(`${MINIAPP_BASE}/api/quota`, { headers: getAuthHeader() })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

// ── Главная функция инициализации ─────────────────────────────────────────────

export interface AuthResult {
  token:     string
  user:      TgUserInfo | null
  settings:  ServerSettings
  favorites: FavoriteItem[]
}

/**
 * Инициализация авторизации при загрузке приложения.
 * Автоматически определяет контекст (Mini App или браузер).
 */
export async function initAuth(): Promise<AuthResult | null> {
  let token: string | null = null

  // 1. Пробуем Mini App initData
  const initData = getTelegramInitData()
  if (initData) {
    try {
      const { access_token, refresh_token } = await loginWithInitData(initData)
      token = access_token
      _token = token
      if (typeof window !== 'undefined') {
        localStorage.setItem(REFRESH_KEY, refresh_token)
      }
    } catch (e) {
      console.warn('initData auth failed:', e)
    }
  }

  // 2. Тихий рефреш через saved refresh_token
  if (!token) {
    token = await _silentRefresh()
  }

  if (!token) return null

  // Параллельно загружаем данные пользователя
  const [user, settings, favorites] = await Promise.all([
    fetchMe(),
    fetchSettings(),
    fetchFavorites(),
  ])

  return { token, user, settings, favorites }
}

/**
 * Полная авторизация через Telegram Login Widget.
 * Вызывается после того как пользователь нажал кнопку и прошёл авторизацию.
 */
export async function loginWithWidgetAndInit(
  data: TelegramWidgetData
): Promise<AuthResult> {
  const { access_token, refresh_token } = await loginWithWidget(data)
  _token = access_token
  if (typeof window !== 'undefined') {
    localStorage.setItem(REFRESH_KEY, refresh_token)
  }

  const [user, settings, favorites] = await Promise.all([
    fetchMe(),
    fetchSettings(),
    fetchFavorites(),
  ])

  return {
    token: access_token,
    user,
    settings,
    favorites,
  }
}

export function logout() {
  clearToken()
}
