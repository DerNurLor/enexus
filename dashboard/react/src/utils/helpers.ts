// ── Date formatting ────────────────────────────────────────────────────────

export function fmtDate(iso?: string): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso.includes('T') ? iso : iso + 'T00:00:00Z')
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

export function fmtTime(iso?: string): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso.includes('T') ? iso : iso + 'T00:00:00Z')
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function fmtDateTime(iso?: string): string {
  if (!iso) return '—'
  return `${fmtDate(iso)} ${fmtTime(iso)}`.trim()
}

export function timeAgo(iso?: string): string {
  if (!iso) return '—'
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 60) return 'только что'
    if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`
    if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`
    if (diff < 604800) return `${Math.floor(diff / 86400)} дн назад`
    return fmtDate(iso)
  } catch {
    return iso
  }
}

// ── Number formatting ──────────────────────────────────────────────────────

export function numFmt(n?: number | null): string {
  if (n == null) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

// ── User initials ──────────────────────────────────────────────────────────

export function initials(name?: string): string {
  if (!name) return '?'
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')
}

// ── Class name helper ──────────────────────────────────────────────────────

export function cx(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}

// ── Safe string escape (for display purposes in HTML injection-free context)

export function esc(s: unknown): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// ── Debounce ───────────────────────────────────────────────────────────────

export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  ms: number
): (...args: Parameters<T>) => void {
  let t: ReturnType<typeof setTimeout>
  return (...args) => {
    clearTimeout(t)
    t = setTimeout(() => fn(...args), ms)
  }
}

// ── Avatar URL ────────────────────────────────────────────────────────────

const PREFIX = (window as Window & { __ADMIN_PREFIX__?: string }).__ADMIN_PREFIX__ || ''

export function avatarUrl(tgId?: number): string | undefined {
  if (!tgId) return undefined
  return `${PREFIX}/dashboard/api/admin/users/${tgId}/avatar`
}
