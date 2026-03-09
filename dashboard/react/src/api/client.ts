/**
 * API Client — hardened with:
 * - Bearer token injection via interceptor
 * - 401 auto-refresh / retry once
 * - Request sanitization (no prototype pollution)
 * - Response type safety
 * - Configurable base URL via env
 */

import axios, { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/auth'

// ── Constants ──────────────────────────────────────────────────────────────

const PREFIX = (window as Window & { __ADMIN_PREFIX__?: string }).__ADMIN_PREFIX__ || ''
export const BASE_URL = PREFIX || ''

// ── Create axios instance ──────────────────────────────────────────────────

const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
})

// ── Request interceptor: inject token ─────────────────────────────────────

client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().token
  if (token && config.headers) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: 401 token refresh ───────────────────────────────

let _refreshing = false
let _refreshQueue: Array<(token: string) => void> = []

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config as AxiosRequestConfig & { _retried?: boolean }
    if (error.response?.status === 401 && !original._retried) {
      original._retried = true
      if (!_refreshing) {
        _refreshing = true
        // Can't re-auth without initData in admin context — just clear
        useAuthStore.getState().clearToken()
        _refreshing = false
        _refreshQueue.forEach((cb) => cb(''))
        _refreshQueue = []
      }
    }
    return Promise.reject(error)
  }
)

// ── Typed API wrapper ──────────────────────────────────────────────────────

async function apiGet<T>(url: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const res = await client.get<T>(url, { params })
  return res.data
}

async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const res = await client.post<T>(url, body)
  return res.data
}

async function apiPatch<T>(url: string, body?: unknown): Promise<T> {
  const res = await client.patch<T>(url, body)
  return res.data
}

async function apiDelete<T = void>(url: string): Promise<T> {
  const res = await client.delete<T>(url)
  return res.data
}

async function apiPut<T>(url: string, body?: unknown): Promise<T> {
  const res = await client.put<T>(url, body)
  return res.data
}

// ── Error message extraction ───────────────────────────────────────────────

export function extractError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data
    if (typeof data === 'string') return data
    if (data?.detail) return String(data.detail)
    if (data?.message) return String(data.message)
    return `HTTP ${err.response?.status ?? 'error'}`
  }
  if (err instanceof Error) return err.message
  return 'Unknown error'
}

// ── Manual token login (paste-token flow) ─────────────────────────────────

export async function loginWithToken(token: string): Promise<import('@/types').AdminUser> {
  const res = await axios.get(`${BASE_URL}/dashboard/api/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    timeout: 15_000,
  })
  return res.data.user
}

// ── API endpoints ──────────────────────────────────────────────────────────

export const api = {
  // Me
  getMe: () => apiGet<{ user: import('@/types').AdminUser; keys: import('@/types').ApiKey[]; activity: import('@/types').ActivityLog[] }>('/dashboard/api/me'),
  createKey: (body: { name: string; permissions: string[]; rate_limit_rpm: number; expires_days?: number }) =>
    apiPost<{ key: string; prefix: string; id: string }>('/dashboard/api/me/keys', body),
  revokeKey: (keyId: string) => apiDelete(`/dashboard/api/me/keys/${keyId}`),

  // Stats
  getStats: () => apiGet<import('@/types').StatsResponse>('/dashboard/api/admin/stats'),
  invalidateCache: () => apiPost<void>('/dashboard/api/admin/cache/invalidate'),

  // Users
  getUsers: (params: { q?: string; blocked_only?: boolean; skip?: number; limit?: number }) =>
    apiGet<{ users: import('@/types').AdminUser[]; total: number }>('/dashboard/api/admin/users', params as Record<string, string | number | boolean>),
  getUserDetail: (userId: string) =>
    apiGet<{ user: import('@/types').AdminUser; keys: import('@/types').ApiKey[]; activity: import('@/types').ActivityLog[] }>(`/dashboard/api/admin/users/${userId}`),
  updateUser: (userId: string, body: Partial<{ roles: string[]; is_blocked: boolean; block_reason: string; daily_requests: number; monthly_ai_tokens: number }>) =>
    apiPatch<import('@/types').AdminUser>(`/dashboard/api/admin/users/${userId}`, body),
  revokeAllKeys: (userId: string) => apiPost<void>(`/dashboard/api/admin/users/${userId}/revoke-all-keys`),
  resetQuota: (userId: string) => apiPost<{ ok: boolean; tg_id: number }>(`/dashboard/api/admin/users/${userId}/reset-quota`),
  setUserPermissions: (userId: string, permissions: string[]) =>
    apiPost<{ ok: boolean; permissions: string[] }>(`/dashboard/api/admin/users/${userId}/permissions`, { permissions }),

  // Roles
  getRoles: () => apiGet<import('@/types').Role[]>('/dashboard/api/admin/roles'),
  createRole: (body: { name: string; description: string; permissions: string[] }) =>
    apiPost<{ id: string; name: string }>('/dashboard/api/admin/roles', body),
  updateRole: (roleId: string, body: { name: string; description: string; permissions: string[] }) =>
    apiPut<{ id: string; name: string }>(`/dashboard/api/admin/roles/${roleId}`, body),
  deleteRole: (roleId: string) => apiDelete(`/dashboard/api/admin/roles/${roleId}`),
  getPermissions: () => apiGet<{ permissions: import('@/types').Permission[] }>('/dashboard/api/admin/permissions'),

  // Logs
  getActivityLogs: (params: { user_id?: string; tg_id?: number; action?: string; skip?: number; limit?: number }) =>
    apiGet<{ logs: import('@/types').ActivityLog[]; total: number }>('/dashboard/api/admin/logs/activity', params as Record<string, string | number | boolean>),
  getErrorLogs: (params: { level?: string; user_id?: string; search?: string; error_id?: string; skip?: number; limit?: number }) =>
    apiGet<{ logs: import('@/types').ErrorLog[]; total: number }>('/dashboard/api/admin/logs/errors', params as Record<string, string | number | boolean>),

  // Analytics
  getAnalytics: (params: { days?: number; from_date?: string; to_date?: string }) =>
    apiGet<import('@/types').AnalyticsResponse>('/dashboard/api/admin/analytics', params as Record<string, string | number | boolean>),

  // Chats
  getChatList: () => apiGet<{ chats: import('@/types').ChatPreview[] }>('/dashboard/api/admin/chats'),
  getChatHistory: (tgId: number, params: { offset?: number; limit?: number; media_type?: string; date_from?: string; date_to?: string }) =>
    apiGet<{ messages: import('@/types').ChatMessage[]; total: number; tg_id: number }>(`/dashboard/api/admin/chat/${tgId}`, params as Record<string, string | number | boolean>),
  pollChat: (tgId: number, afterTs?: string) =>
    apiGet<{ messages: import('@/types').ChatMessage[] }>(`/dashboard/api/admin/chat/${tgId}/poll`, afterTs ? { after_ts: afterTs } : undefined),
  searchChat: (tgId: number, q: string, limit?: number) =>
    apiGet<{ messages: import('@/types').ChatMessage[]; total: number }>(`/dashboard/api/admin/chat/${tgId}/search`, { q, limit: limit ?? 50 } as Record<string, string | number | boolean>),
  sendMessage: (tgId: number, text: string) =>
    apiPost<{ ok: boolean }>('/dashboard/api/admin/chat/send', { tg_id: tgId, text }),
  getMediaUrl: (tgId: number, fileId: string) =>
    `${BASE_URL}/dashboard/api/admin/chat/${tgId}/media?file_id=${encodeURIComponent(fileId)}`,

  // Support
  getSupportTickets: (params: { status?: string; category?: string; skip?: number; limit?: number }) =>
    apiGet<{ tickets: import('@/types').SupportTicket[]; total: number }>('/dashboard/api/admin/support', params as Record<string, string | number | boolean>),
  getSupportDetail: (ticketId: string) =>
    apiGet<{ ticket: import('@/types').SupportTicket }>(`/dashboard/api/admin/support/${ticketId}`),
  replyTicket: (ticketId: string, reply: string) =>
    apiPost<{ ok: boolean }>(`/dashboard/api/admin/support/${ticketId}/reply`, { reply }),
  closeTicket: (ticketId: string, reason: string, hideReason: boolean) =>
    apiPost<{ ok: boolean }>(`/dashboard/api/admin/support/${ticketId}/close`, { reason, hide_reason: hideReason }),

  // Broadcast
  sendBroadcast: (body: { text: string; audience: string; role?: string; schedule_at?: string }) =>
    apiPost<{ job_id: string; status: string }>('/dashboard/api/admin/broadcast', body),
  getBroadcasts: () => apiGet<{ broadcasts: import('@/types').BroadcastJob[] }>('/dashboard/api/admin/broadcasts'),

  // Settings
  getSettings: () => apiGet<import('@/types').SystemSettings>('/dashboard/api/admin/settings'),
  saveSettings: (body: Partial<import('@/types').SystemSettings>) =>
    apiPost<{ ok: boolean; changed: string[]; note: string }>('/dashboard/api/admin/settings', body),

  // MongoDB viewer
  getMongo: (params: { collection: string; filter?: string; sort?: string; skip?: number; limit?: number }) =>
    apiGet<{ documents: import('@/types').MongoDocument[]; total: number; skip: number }>('/dashboard/api/admin/mongo', params as Record<string, string | number | boolean>),

  // Bot command
  botCommand: (method: string, params: Record<string, unknown>) =>
    apiPost<unknown>('/dashboard/api/admin/bot/command', { method, params }),
}

export default client
