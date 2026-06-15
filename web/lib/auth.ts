/**
 * Безопасность:
 *  - access token  — только в памяти (не переживает reload)
 *  - refresh token — localStorage (переживает reload, используется для тихого входа)
 *  [F1] Refresh token удаляется при 401/403 от /auth/refresh, но не при сетевых ошибках.
 *  [F3] loginWithBotToken: токен очищается только при 401/403, не при 5xx.
 */

const AUTH_BASE    = (process.env.NEXT_PUBLIC_API_URL || '') + '/auth'
const MINIAPP_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/miniapp'
const REFRESH_KEY  = 'ncfu_refresh_token'

/** fetch с таймаутом — не висит на плохой сети */
async function fetchWithTimeout(url: string, opts: RequestInit = {}, ms = 8000): Promise<Response> {
  const ctrl = new AbortController()
  const id   = setTimeout(() => ctrl.abort(), ms)
  try {
    return await fetch(url, { ...opts, signal: ctrl.signal })
  } finally {
    clearTimeout(id)
  }
}

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
  profile_role?:         string | null
  profile_group_id?:     number | null
  profile_group_name?:   string | null
  profile_teacher_id?:   number | null
  profile_teacher_name?: string | null
  weekFromMonday?:   boolean
  time24h?:          boolean
  compact?:          boolean
  notifications?:    boolean
  default_group?:    string | null
  default_teacher?:  string | null
  theme?:            string
  accent_color?:     string
  profile_group_confirmed?: boolean
}

export interface QuotaStatus {
  used:      number
  cap:       number
  remaining: number
  ttl_secs:  number
  ttl_hours: number
  exhausted: boolean
}

export interface FavoriteItem {
  type:  'group' | 'teacher'
  id:    string | number
  name:  string
}

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

let _refreshInProgress: Promise<string | null> | null = null

async function _silentRefresh(): Promise<string | null> {
  if (_refreshInProgress) {
    return _refreshInProgress
  }
  _refreshInProgress = _doSilentRefresh().finally(() => { _refreshInProgress = null })
  return _refreshInProgress
}

async function _doSilentRefresh(attempt = 0): Promise<string | null> {
  if (typeof window === 'undefined') return null
  const refresh = localStorage.getItem(REFRESH_KEY)
  if (!refresh) return null

  try {
    const res = await fetchWithTimeout(`${AUTH_BASE}/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    }, 8000)

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        localStorage.removeItem(REFRESH_KEY)
      }
      return null
    }
    const { access_token, refresh_token } = await res.json()
    _token = access_token
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token)
    return access_token
  } catch (e: any) {
    // Сетевая ошибка или таймаут — retry один раз с задержкой
    if (attempt === 0 && (e?.name === 'AbortError' || e?.name === 'TypeError')) {
      await new Promise(r => setTimeout(r, 1500))
      return _doSilentRefresh(1)
    }
    // Не удаляем токен при сетевых ошибках
    return null
  }
}


export async function fetchMe(): Promise<TgUserInfo | null> {
  if (!_token) return null
  try {
    const res = await fetchWithTimeout(`${AUTH_BASE}/me`, { headers: getAuthHeader() }, 6000)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function fetchSettings(): Promise<ServerSettings> {
  try {
    const res = await fetchWithTimeout(`${MINIAPP_BASE}/api/settings`, { headers: getAuthHeader() }, 6000)
    if (!res.ok) return {}
    const data = await res.json()
    return (data?.settings ?? data) as ServerSettings
  } catch {
    return {}
  }
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

export async function fetchQuota(): Promise<QuotaStatus | null> {
  if (!_token) return null
  try {
    const res = await fetch(`${MINIAPP_BASE}/api/profile/limits`, { headers: getAuthHeader() })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export interface AuthResult {
  token:     string
  user:      TgUserInfo | null
  settings:  ServerSettings
  favorites: FavoriteItem[]
}

export async function initAuth(): Promise<AuthResult | null> {
  let token: string | null = null

  const tg = typeof window !== 'undefined' ? (window as any).Telegram?.WebApp : null
  const isRealMiniApp = !!(tg?.initData && tg.initData.length > 0 && tg?.platform && tg.platform !== 'unknown')

  if (isRealMiniApp) {
    try {
      const { access_token, refresh_token } = await loginWithInitData(tg.initData)
      token = access_token
      _token = token
      if (typeof window !== 'undefined') {
        localStorage.setItem(REFRESH_KEY, refresh_token)
      }
    } catch (e) {
      console.warn('[auth] initData auth failed:', e)
    }
  }

  if (!token) {
    token = await _silentRefresh()
  }

  if (!token) return null

  // Загружаем профиль параллельно, но с таймаутом — на плохой сети не блокируем
  const [user, settings, favorites] = await Promise.all([
    fetchMe().catch(() => null),
    fetchSettings().catch(() => ({})),
    fetchFavorites().catch(() => []),
  ])

  return { token, user: user as any, settings, favorites }
}

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

// Алиас для обратной совместимости с Providers.tsx
export const authenticateWithTelegram = initAuth

export async function loginWithBotToken(botToken: string): Promise<AuthResult> {
  const res = await fetch(`${AUTH_BASE}/bot/exchange`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: botToken }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    // [F3] Сбрасываем токен только при явном отказе (401/403), не при 5xx
    if (res.status === 401 || res.status === 403) {
      _token = null
    }
    throw new Error(err.detail || 'Токен входа истёк. Запросите новый через бота: /start login')
  }
  const { access_token, refresh_token } = await res.json()
  _token = access_token
  if (typeof window !== 'undefined') localStorage.setItem(REFRESH_KEY, refresh_token)
  const [user, settings, favorites] = await Promise.all([fetchMe(), fetchSettings(), fetchFavorites()])
  return { token: access_token, user, settings, favorites }
}
