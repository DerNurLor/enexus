'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { CalendarDays, User, GraduationCap, DoorOpen } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/schedule', label: 'Расписание', icon: CalendarDays },
  { href: '/rooms',    label: 'Аудитории',  icon: DoorOpen },
  { href: '/profile',  label: 'Профиль',    icon: User },
]

export function DesktopSidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 z-50 flex flex-col"
      style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)' }}>
      <div className="p-6 flex items-center gap-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: 'var(--cyan-dim)', border: '1px solid rgba(92,225,230,0.3)' }}>
          <GraduationCap size={18} style={{ color: 'var(--cyan)' }} />
        </div>
        <div>
          <div className="text-sm font-bold text-white tracking-wide">НЦФУ</div>
          <div className="text-[10px]" style={{ color: 'var(--t-muted)' }}>Студенческий портал</div>
        </div>
      </div>

      <nav className="flex-1 p-3 flex flex-col gap-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link key={href} href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 hover:bg-white/5"
              style={active
                ? { background: 'var(--cyan-dim)', color: 'var(--cyan)', borderLeft: '3px solid var(--cyan)', paddingLeft: 9 }
                : { color: 'var(--t-secondary)', borderLeft: '3px solid transparent', paddingLeft: 9 }}>
              <Icon size={18} strokeWidth={active ? 2.5 : 1.8} />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="p-4" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="text-[10px] text-center" style={{ color: 'var(--t-muted)' }}>© 2026 НЦФУ</div>
      </div>
    </aside>
  )
}
