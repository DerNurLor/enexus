'use client'
/**
 * web/components/layout/DesktopSidebar.tsx
 *
 * Боковая панель для desktop-версии.
 * Показывает бейдж с количеством новых оценок на пункте «Предметы».
 */
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  CalendarDays, BookOpen, User, Map,
} from 'lucide-react'
import { useScheduleStore } from '@/lib/store'

const NAV_ITEMS = [
  { href: '/schedule', label: 'Расписание', icon: CalendarDays },
  { href: '/map',      label: 'Карта',       icon: Map          },
  { href: '/ecampus',  label: 'Предметы',    icon: BookOpen     },
  { href: '/profile',  label: 'Профиль',     icon: User         },
]

export function DesktopSidebar() {
  const pathname = usePathname()
  const newGradesCount = useScheduleStore((s) => s.newGradesCount)

  return (
    <aside
      className="fixed left-0 top-0 h-full w-64 flex flex-col z-30"
      style={{ background: 'var(--card)', borderRight: '1px solid var(--border)' }}
    >
      {/* Logo */}
      <div className="px-6 pt-8 pb-6">
        <span className="text-lg font-bold" style={{ color: 'var(--t-primary)' }}>
          НЦФУ
        </span>
        <p className="text-[11px] mt-0.5" style={{ color: 'var(--t-muted)' }}>
          Расписание
        </p>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-3 flex flex-col gap-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/')
          const isEcampus = href === '/ecampus'
          const badge = isEcampus && newGradesCount > 0 ? newGradesCount : 0

          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all relative"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--accent) 12%, transparent)' : 'transparent',
                color:      isActive ? 'var(--accent)' : 'var(--t-secondary)',
              }}
            >
              <div className="relative shrink-0">
                <Icon
                  size={18}
                  strokeWidth={isActive ? 2.2 : 1.6}
                />
                {badge > 0 && (
                  <span
                    className="absolute -top-1.5 -right-2 min-w-[16px] h-4 flex items-center justify-center px-1 text-[9px] font-bold rounded-full"
                    style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}
                  >
                    {badge > 9 ? '9+' : badge}
                  </span>
                )}
              </div>
              {label}

              {/* Active indicator */}
              {isActive && (
                <div
                  className="ml-auto w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: 'var(--accent)' }}
                />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 pb-6 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
        <p className="text-[10px]" style={{ color: 'var(--t-muted)' }}>
          v2.0 · СКФУ Расписание
        </p>
      </div>
    </aside>
  )
}
