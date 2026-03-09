export function esc(s: unknown): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export function isoToday(): string {
  return new Date().toISOString().split('T')[0];
}

export function isoOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
}

export type DateQuick = 'today' | 'tomorrow' | 'week' | 'next-week';

export function getDateRange(q: DateQuick): { from: string; to: string } {
  const today = new Date();
  const wd = today.getDay();
  const mon = wd === 0 ? -6 : 1 - wd;

  if (q === 'today') {
    const s = isoToday();
    return { from: s, to: s };
  }
  if (q === 'tomorrow') {
    const s = isoOffset(1);
    return { from: s, to: s };
  }
  if (q === 'week') {
    const d = new Date();
    d.setDate(d.getDate() + mon);
    const from = d.toISOString().split('T')[0];
    d.setDate(d.getDate() + 6);
    const to = d.toISOString().split('T')[0];
    return { from, to };
  }
  // next-week
  const d = new Date();
  d.setDate(d.getDate() + mon + 7);
  const from = d.toISOString().split('T')[0];
  d.setDate(d.getDate() + 6);
  const to = d.toISOString().split('T')[0];
  return { from, to };
}

const MONTHS = ['', 'янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
const WDAYS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];

export function fmtDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return `${WDAYS[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth() + 1]}`;
}

export const LT_KEY: Record<string, string> = {
  'Лекция': 'lec',
  'Практическое занятие': 'prac',
  'Лабораторная работа': 'lab',
  'Семинар': 'prac',
  'Зачёт': 'zach',
  'Экзамен': 'exam',
};

export const LT_SHORT: Record<string, string> = {
  'Лекция': 'ЛЕК',
  'Практическое занятие': 'ПР',
  'Лабораторная работа': 'ЛАБ',
  'Семинар': 'СЕМ',
  'Зачёт': 'ЗАЧ',
  'Экзамен': 'ЭКЗ',
};
