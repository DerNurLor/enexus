// ── Auth & User Types ──────────────────────────────────────────────────────

export interface AdminUser {
  id: string
  tg_id: number
  username?: string
  first_name: string
  last_name: string
  display: string
  avatar?: string
  roles: string[]
  is_blocked: boolean
  block_reason?: string
  last_active?: string
  created_at?: string
  daily_requests: number | null
  quota_cap: number
  monthly_ai_tokens: number
  extra_permissions: string[]
  accent_color: string
}

export interface UserQuota {
  used: number
  cap: number
  remaining: number
  ttl_secs: number
  exhausted: boolean
}

export interface ApiKey {
  id: string
  prefix: string
  name: string
  permissions: string[]
  rate_limit_rpm: number
  expires_at?: string
  last_used_at?: string
  created_at: string
  use_count: number
  is_revoked?: boolean
}

// ── Activity & Logs ────────────────────────────────────────────────────────

export interface ActivityLog {
  id: string
  user_id?: string
  tg_id?: number
  action: string
  ip?: string
  details?: Record<string, unknown>
  timestamp: string
}

export interface ErrorLog {
  id: string
  error_id?: string
  level: string
  message: string
  traceback?: string
  user_id?: string
  tg_id?: number
  path?: string
  intent?: string
  user_text?: string
  timestamp: string
}

// ── Stats & Analytics ──────────────────────────────────────────────────────

export interface StatTotals {
  users: number
  blocked: number
  active_today: number
  open_tickets: number
  total_lessons: number
  total_groups: number
  total_teachers: number
  bot_messages_today: number
  api_calls_today: number
}

export interface DailyActivity {
  date: string
  count: number
}

export interface ActionBreakdown {
  action: string
  count: number
}

export interface RecentEvent {
  user_id?: string
  tg_id?: number
  action: string
  timestamp: string
}

export interface ScrapeLog {
  mode: string
  groups_scraped: number
  lessons_upserted: number
  status: string
  started_at: string
  finished_at: string
}

export interface StatsResponse {
  totals: StatTotals
  daily_activity: DailyActivity[]
  action_breakdown: ActionBreakdown[]
  recent_events: RecentEvent[]
  scrape_stats: { recent: ScrapeLog[] }
}

export interface AnalyticsResponse {
  period: { from: string; to: string; days: number }
  totals: {
    messages: number
    errors: number
    fb_likes: number
    fb_dislikes: number
    fb_pending: number
    fb_total: number
    fb_pct_like: number
  }
  daily_messages: { date: string; role: string; count: number }[]
  daily_errors: { date: string; count: number }[]
  daily_feedback: { date: string; rating: string; count: number }[]
  intent_breakdown: { intent: string; count: number }[]
  error_by_intent: { intent: string; count: number }[]
  top_error_queries: { query: string; count: number }[]
  hourly_heatmap: { hour: number; count: number }[]
  new_users_daily: { date: string; count: number }[]
  miniapp_actions: { action: string; count: number }[]
}

// ── Chat / Messages ────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string
  tg_id: number
  message_id?: number
  role: string
  first_name: string
  last_name: string
  username: string
  text: string
  html_text: string
  timestamp: string
  is_forward: boolean
  forward_from_name?: string
  forward_from_chat?: string
  forward_date?: string
  reply_to_message_id?: number
  reply_to_text?: string
  media_type?: string
  file_id?: string
  file_unique_id?: string
  file_name?: string
  file_size?: number
  mime_type?: string
  duration?: number
  width?: number
  height?: number
  thumbnail_file_id?: string
  sticker_emoji?: string
  media_url?: string
  extra?: Record<string, unknown>
}

export interface ChatPreview {
  tg_id: number
  display: string
  username?: string
  avatar?: string
  last_text: string
  last_role: string
  last_ts: string
  msg_count: number
  is_blocked: boolean
}

// ── Support Tickets ────────────────────────────────────────────────────────

export interface SupportTicket {
  id: string
  tg_id?: number
  username?: string
  first_name: string
  message: string
  status: 'open' | 'answered' | 'closed'
  category: 'bug' | 'suggestion' | 'question' | 'other'
  source: string
  admin_reply?: string
  replied_at?: string
  close_reason?: string
  close_reason_hidden: boolean
  closed_by?: string
  closed_at?: string
  created_at: string
}

// ── Roles ─────────────────────────────────────────────────────────────────

export interface Role {
  id: string
  name: string
  description: string
  permissions: string[]
  created_at: string
}

export interface Permission {
  perm: string
  group: string
  description: string
}

// ── Broadcast ─────────────────────────────────────────────────────────────

export interface BroadcastJob {
  id: string
  text: string
  audience: string
  status: string
  sent_count: number
  created_at: string
}

// ── Settings ──────────────────────────────────────────────────────────────

export interface SystemSettings {
  app_env?: string
  log_level?: string
  scrape_interval_hours?: number
  scraper_concurrency?: number
  scraper_request_delay?: number
  scrape_mode?: string
  academic_year_start?: number
  rate_limit_user_rpm?: number
  rate_limit_anon_rpm?: number
  rate_limit_bot_rpm?: number
  rate_limit_window?: number
  cache_ttl_now?: number
  cache_ttl_day?: number
  cache_ttl_week?: number
  cache_ttl_search?: number
  cache_ttl_meta?: number
  webhook_base_url?: string
  sentry_traces_rate?: number
  activity_log_ttl_days?: number
  cleanup_hour_utc?: number
  telegram_bot_configured?: boolean
  openai_configured?: boolean
  sentry_configured?: boolean
  redis_password_configured?: boolean
  mongo_auth_configured?: boolean
}

// ── MongoDB Viewer ────────────────────────────────────────────────────────

export type MongoDocument = Record<string, unknown>

// ── Navigation ────────────────────────────────────────────────────────────

export type PanelId =
  | 'overview'
  | 'users'
  | 'chats'
  | 'support'
  | 'broadcast'
  | 'roles'
  | 'activity'
  | 'errors'
  | 'analytics'
  | 'feedback'
  | 'mongo'
  | 'settings'

export interface NavItem {
  id: PanelId
  label: string
  group: string
  badge?: number | string
}
