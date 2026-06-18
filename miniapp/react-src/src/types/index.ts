export interface TelegramWebApp {
  ready(): void;
  expand(): void;
  close(): void;
  initData: string;
  initDataUnsafe: {
    user?: TelegramUser;
  };
  colorScheme: 'light' | 'dark';
  themeParams: Record<string, string>;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  HapticFeedback?: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void;
    notificationOccurred(type: 'error' | 'success' | 'warning'): void;
  };
}

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  language_code?: string;
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

export interface User {
  id: string;
  tg_id: number;
  first_name: string;
  last_name: string;
  username?: string;
  display: string;
  avatar?: string;
  roles: string[];
  permissions: string[];
  is_blocked: boolean;
  is_beta: boolean;
  is_vip: boolean;
  is_admin: boolean;
}

export interface Lesson {
  timeStart: string;
  timeEnd: string;
  subject: string;
  lessonType: string;
  teacherName?: string;
  groupName?: string;
  roomName?: string;
  building?: string;
  subgroup?: number;
  weekNumber?: number;
}

export interface Day {
  date: string;
  weekday: number;
  weekdayName: string;
  weekNumber?: number;
  lessons: Lesson[];
}

export interface ScheduleResponse {
  days: Day[];
  meta: {
    total: number;
    is_beta: boolean;
    is_vip: boolean;
  };
}

export interface Favorite {
  type: 'group' | 'teacher' | 'room';
  id: string;
  label: string;
}

export interface Institute {
  institute_id: number;
  short_name: string;
  name: string;
  buildings: string[];
}

export interface SearchResult {
  groups: Array<{ groupId: number; name: string; instituteName: string; course?: number }>;
  teachers: Array<{ teacherId: number; fullName: string; shortName: string }>;
  rooms: Array<{ roomId: number; name: string; building?: string }>;
}

export interface QuotaStatus {
  used: number;
  cap: number;
  remaining: number;
  exhausted: boolean;
  ttl_secs: number;
}

export type SearchType = 'group' | 'teacher' | 'room';
export type Page = 'schedule' | 'rooms' | 'favorites' | 'profile';
export type Theme = 'auto' | 'light' | 'dark';

export interface Settings {
  weekFromMonday?: boolean;
  time24h?: boolean;
  compact?: boolean;
  notifications?: boolean;
  theme?: Theme;
  accent_color?: string;
  language?: string;
}
