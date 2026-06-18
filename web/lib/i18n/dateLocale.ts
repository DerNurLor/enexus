import { ru, enUS, zhCN, ar, es, fr, tr, kk, az, hy, uz, hi, vi, type Locale } from 'date-fns/locale'

// date-fns не имеет локали для таджикского — используем русскую (кириллица, близкий формат).
export const DATE_FNS_LOCALES: Record<string, Locale> = {
  ru, en: enUS, zh: zhCN, ar, es, fr, tr, kk, az, hy, uz, tg: ru, hi, vi,
}

export const INTL_LOCALE_TAGS: Record<string, string> = {
  ru: 'ru-RU', en: 'en-US', zh: 'zh-CN', ar: 'ar-SA', es: 'es-ES', fr: 'fr-FR',
  tr: 'tr-TR', kk: 'kk-KZ', az: 'az-AZ', hy: 'hy-AM', uz: 'uz-UZ', tg: 'ru-RU',
  hi: 'hi-IN', vi: 'vi-VN',
}

export function dateFnsLocale(lang: string): Locale {
  return DATE_FNS_LOCALES[lang] ?? ru
}

export function intlLocale(lang: string): string {
  return INTL_LOCALE_TAGS[lang] ?? 'ru-RU'
}
