'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { CalendarDays, User, DoorOpen } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/schedule', label: 'Расписание', icon: CalendarDays },
  { href: '/rooms',    label: 'Аудитории',  icon: DoorOpen },
  { href: '/profile',  label: 'Профиль',    icon: User },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden"
      style={{
        background: 'rgba(16,16,16,0.92)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid var(--border)',
        paddingBottom: 'var(--safe-bottom)',
      }}>
      <div className="flex items-center justify-around h-16 px-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link key={href} href={href} className="nav-btn" style={{ minWidth: 72 }}>
              <Icon size={22} strokeWidth={active ? 2.5 : 1.8}
                style={{ color: active ? 'var(--cyan)' : 'var(--t-muted)', transition: 'color 0.2s' }} />
              <span className="text-[10px] font-medium tracking-wide"
                style={{ color: active ? 'var(--cyan)' : 'var(--t-muted)', transition: 'color 0.2s' }}>
                {label}
              </span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
