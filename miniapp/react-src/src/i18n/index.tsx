import React, { createContext, useContext, useState, useCallback, useMemo } from 'react'

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

export const LOCALES: Record<string, { MESSAGES: Record<string, string>; MONTHS: string[]; WDAYS: string[] }> = {
  ru, en, zh, ar, es, fr, tr, kk, az, hy, uz, tg, hi, vi,
}

export const LANGUAGE_NAMES: Record<string, string> = {
  ru: 'Русский', en: 'English', zh: '中文', ar: 'العربية',
  es: 'Español', fr: 'Français', tr: 'Türkçe', kk: 'Қазақша',
  az: 'Azərbaycan', hy: 'Հայերեն', uz: "O'zbek", tg: 'Тоҷикӣ',
  hi: 'हिन्दी', vi: 'Tiếng Việt',
}

export const SUPPORTED_LANGUAGES = Object.keys(LOCALES)

export function resolveTelegramLang(languageCode: string | null | undefined): string {
  if (!languageCode) return DEFAULT_LANG
  const code = languageCode.toLowerCase().split('-')[0]
  return code in LOCALES ? code : DEFAULT_LANG
}

function format(template: string, vars?: Record<string, unknown>): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (m, key) => (key in vars ? String(vars[key]) : m))
}

interface I18nContextValue {
  lang: string
  setLang: (lang: string) => void
  t: (key: string, vars?: Record<string, unknown>) => string
  months: string[]
  wdays: string[]
}

const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({
  children, initialLang,
}: { children: React.ReactNode; initialLang?: string }) {
  const [lang, setLang] = useState(initialLang && initialLang in LOCALES ? initialLang : DEFAULT_LANG)

  const t = useCallback((key: string, vars?: Record<string, unknown>) => {
    const table = LOCALES[lang]?.MESSAGES ?? LOCALES[DEFAULT_LANG].MESSAGES
    const template = table[key] ?? LOCALES[DEFAULT_LANG].MESSAGES[key] ?? key
    return format(template, vars)
  }, [lang])

  const value = useMemo<I18nContextValue>(() => ({
    lang,
    setLang: (l: string) => setLang(l in LOCALES ? l : DEFAULT_LANG),
    t,
    months: LOCALES[lang]?.MONTHS ?? LOCALES[DEFAULT_LANG].MONTHS,
    wdays: LOCALES[lang]?.WDAYS ?? LOCALES[DEFAULT_LANG].WDAYS,
  }), [lang, t])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
