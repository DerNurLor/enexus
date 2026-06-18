import { useCallback } from 'react'
import { useScheduleStore } from '@/lib/store'

import * as ru from './locales/ru'
import * as en from './locales/en'
import * as zh from './locales/zh'
import * as ar from './locales/ar'
import * as es from './locales/es'
import * as fr from './locales/fr'
import * as tr from './locales/tr'
import * as kk from './locales/kk'
import * as az from './locales/az'
import * as hy from './locales/hy'
import * as uz from './locales/uz'
import * as tg from './locales/tg'
import * as hi from './locales/hi'
import * as vi from './locales/vi'

export const DEFAULT_LANG = 'ru'

export const LOCALES: Record<string, { MESSAGES: Record<string, string> }> = {
  ru, en, zh, ar, es, fr, tr, kk, az, hy, uz, tg, hi, vi,
}

export const LANGUAGE_NAMES: Record<string, string> = {
  ru: 'Русский', en: 'English', zh: '中文', ar: 'العربية',
  es: 'Español', fr: 'Français', tr: 'Türkçe', kk: 'Қазақша',
  az: 'Azərbaycan', hy: 'Հայերեն', uz: "O'zbek", tg: 'Тоҷикӣ',
  hi: 'हिन्दी', vi: 'Tiếng Việt',
}

export const SUPPORTED_LANGUAGES = Object.keys(LOCALES)

export function resolveBrowserLang(languages: readonly string[] | string | null | undefined): string {
  const list = Array.isArray(languages) ? languages : languages ? [languages] : []
  for (const l of list) {
    const code = l.toLowerCase().split('-')[0]
    if (code in LOCALES) return code
  }
  return DEFAULT_LANG
}

function format(template: string, vars?: Record<string, unknown>): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (m, key) => (key in vars ? String(vars[key]) : m))
}

/** useT — читает текущий язык из общего zustand-стора (settings.language) и возвращает t(). */
export function useT() {
  const lang = useScheduleStore((s) => s.settings.language) || DEFAULT_LANG

  const t = useCallback((key: string, vars?: Record<string, unknown>) => {
    const table = LOCALES[lang]?.MESSAGES ?? LOCALES[DEFAULT_LANG].MESSAGES
    const template = table[key] ?? LOCALES[DEFAULT_LANG].MESSAGES[key] ?? key
    return format(template, vars)
  }, [lang])

  return { t, lang }
}
