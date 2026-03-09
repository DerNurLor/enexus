import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from './Icons'
import { useUIStore } from '@/store/ui'
import { initials } from '@/utils/helpers'
import type { AdminUser } from '@/types'

// ── Spinner ────────────────────────────────────────────────────────────────

export function Spinner({ lg }: { lg?: boolean }) {
  const sz = lg ? 22 : 14
  return (
    <svg width={sz} height={sz} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      style={{ animation: 'spin 0.7s linear infinite', flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" strokeOpacity=".2"/>
      <path d="M12 2a10 10 0 010 20" strokeLinecap="round"/>
    </svg>
  )
}

// ── User Avatar ────────────────────────────────────────────────────────────

export function UserAvatar({ user, size = 24 }: { user: Partial<AdminUser>; size?: number }) {
  const initStr = initials(user.display || user.first_name)
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', background: 'var(--ink-50)', border: '1px solid var(--line3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: size * 0.36, color: 'var(--t-80)', flexShrink: 0, overflow: 'hidden' }}>
      {user.avatar
        ? <img src={user.avatar} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => (e.currentTarget.style.display = 'none')} />
        : initStr
      }
    </div>
  )
}

// ── Status Badge ───────────────────────────────────────────────────────────

export function StatusBadge({ blocked }: { blocked?: boolean }) {
  return blocked
    ? <span className="badge badge-dark" style={{ color: 'var(--t-40)' }}>blocked</span>
    : <span className="badge badge-neutral" style={{ color: 'var(--t-60)' }}>active</span>
}

// ── Role Pills ─────────────────────────────────────────────────────────────

export function RolePills({ roles }: { roles: string[] }) {
  return (
    <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
      {roles.map((r) => (
        <span key={r} className={`role-pill ${r}`}>{r}</span>
      ))}
    </div>
  )
}

// ── Pagination ─────────────────────────────────────────────────────────────

export function Pagination({ page, total, pageSize, onChange }: { page: number; total: number; pageSize: number; onChange: (p: number) => void }) {
  const pages = Math.ceil(total / pageSize)
  if (pages <= 1) return null
  const start = Math.max(0, Math.min(page - 2, pages - 5))
  const nums: number[] = []
  for (let i = 0; i < Math.min(5, pages); i++) nums.push(start + i)
  return (
    <div style={{ display: 'flex', gap: 4, marginTop: 12, alignItems: 'center', justifyContent: 'flex-end' }}>
      <button className="btn btn-ghost btn-icon" onClick={() => onChange(page - 1)} disabled={page === 0}><Icon.chevL /></button>
      {nums.map((n) => (
        <button key={n} className={`btn ${n === page ? 'btn-primary' : 'btn-ghost'}`} style={{ minWidth: 28, padding: '4px 0', fontSize: 10 }} onClick={() => onChange(n)}>{n + 1}</button>
      ))}
      <button className="btn btn-ghost btn-icon" onClick={() => onChange(page + 1)} disabled={page >= pages - 1}><Icon.chevR /></button>
      <span style={{ fontSize: 9, color: 'var(--t-40)', marginLeft: 4 }}>{total} всего</span>
    </div>
  )
}

// ── Skeleton Row ───────────────────────────────────────────────────────────

export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} style={{ paddingLeft: i === 0 ? 16 : undefined }}>
          <div className="skeleton" style={{ height: 10, width: i === 0 ? 120 : 60, borderRadius: 2 }} />
        </td>
      ))}
    </tr>
  )
}

// ── Toast System ───────────────────────────────────────────────────────────

export function ToastRoot() {
  const toasts = useUIStore((s) => s.toasts)
  const remove = useUIStore((s) => s.removeToast)
  return createPortal(
    <div className="toast-root">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div key={t.id} className={`toast-item ${t.type}`}
            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }} onClick={() => remove(t.id)} style={{ cursor: 'pointer' }}>
            {t.msg}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>,
    document.body
  )
}

// ── Confirm Modal ──────────────────────────────────────────────────────────

export function ConfirmModal({ title, body, onConfirm, onCancel, danger }: { title: string; body?: string; onConfirm: () => void; onCancel: () => void; danger?: boolean }) {
  return createPortal(
    <>
      <div className="overlay" onClick={onCancel} />
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}
        style={{ position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', background: 'var(--ink-20)', border: '1px solid var(--line2)', borderRadius: 'var(--rad-lg)', padding: 24, width: 320, zIndex: 200 }}>
        <div style={{ fontFamily: 'var(--serif)', fontSize: 16, color: 'var(--t-100)', marginBottom: body ? 8 : 20 }}>{title}</div>
        {body && <div style={{ fontSize: 11, color: 'var(--t-60)', marginBottom: 20 }}>{body}</div>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onCancel}>Отмена</button>
          <button className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm}>Подтвердить</button>
        </div>
      </motion.div>
    </>,
    document.body
  )
}

// ── Copy Button ────────────────────────────────────────────────────────────

export function CopyBtn({ text, label }: { text: string; label?: string }) {
  const { showToast } = useUIStore()
  const copied = useRef(false)
  async function copy() {
    if (copied.current) return
    copied.current = true
    await navigator.clipboard.writeText(text).catch(() => {})
    showToast('Скопировано', 'ok', 1800)
    setTimeout(() => { copied.current = false }, 2000)
  }
  return (
    <button className="btn btn-ghost btn-icon" onClick={copy} title={label ?? 'Копировать'}>
      <Icon.copy />
    </button>
  )
}

// ── Section Header ─────────────────────────────────────────────────────────

export function SectionHeader({ title, actions }: { title: string; actions?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
      <div style={{ fontFamily: 'var(--serif)', fontSize: 18, fontWeight: 700, color: 'var(--t-100)' }}>{title}</div>
      {actions && <div style={{ display: 'flex', gap: 8 }}>{actions}</div>}
    </div>
  )
}

// ── Empty State ────────────────────────────────────────────────────────────

export function EmptyState({ icon = '∅', text }: { icon?: string; text: string }) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <div className="empty-text">{text}</div>
    </div>
  )
}

// ── Tabs ───────────────────────────────────────────────────────────────────

export function Tabs({ tabs, active, onChange }: { tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div style={{ display: 'flex', gap: 2, marginBottom: 16, borderBottom: '1px solid var(--line)', paddingBottom: 0 }}>
      {tabs.map((t) => (
        <button key={t.id} onClick={() => onChange(t.id)}
          style={{ padding: '6px 14px', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: 11, color: active === t.id ? 'var(--t-100)' : 'var(--t-40)', borderBottom: active === t.id ? '2px solid var(--t-100)' : '2px solid transparent', marginBottom: -1, transition: 'color 0.15s, border-color 0.15s' }}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ── Portal-rendered detail panel ───────────────────────────────────────────

export function DetailPanel({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  return createPortal(
    <>
      <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
      <motion.div className="detail-panel" initial={{ x: 360 }} animate={{ x: 0 }} exit={{ x: 360 }} transition={{ type: 'spring', damping: 26, stiffness: 300 }}>
        {children}
      </motion.div>
    </>,
    document.body
  )
}
