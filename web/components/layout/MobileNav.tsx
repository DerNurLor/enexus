'use client'
/**
 * web/components/layout/MobileNav.tsx
 *
 * Нижняя навигационная панель для мобильной версии.
 * Показывает бейдж с количеством новых оценок на иконке «Предметы».
 */
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  CalendarDays, BookOpen, User, Map,
} from 'lucide-react'
import { useScheduleStore } from '@/lib/store'

export function MobileNav() {
  const pathname = usePathname()
  const newGradesCount = useScheduleStore((s) => s.newGradesCount)
  const profile = useScheduleStore((s) => s.profile)
  const isTeacher = profile?.role === 'teacher'

  const NAV_ITEMS = [
    { href: '/schedule', label: 'Расписание', icon: CalendarDays },
    { href: '/map',      label: 'Карта',       icon: Map          },
    isTeacher
      ? { href: '/teacher', label: 'Занятия', icon: BookOpen }
      : { href: '/ecampus', label: 'Предметы', icon: BookOpen },
    { href: '/profile',  label: 'Профиль',     icon: User         },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 lg:hidden"
      style={{
        background:   'var(--card)',
        borderTop:    '1px solid var(--border)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}>
      <div className="flex items-stretch">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/')
          const badge = href === '/ecampus' && newGradesCount > 0 ? newGradesCount : 0

          return (
            <Link
              key={href}
              href={href}
              className="flex-1 flex flex-col items-center justify-center gap-1 py-2.5 min-h-[56px] relative"
              style={{ color: isActive ? 'var(--accent)' : 'var(--t-muted)' }}
            >
              <div className="relative">
                <Icon
                  size={22}
                  strokeWidth={isActive ? 2.2 : 1.6}
                  style={{ color: isActive ? 'var(--accent)' : 'var(--t-muted)' }}
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
              <span
                className="text-[10px] font-medium leading-none"
                style={{ color: isActive ? 'var(--accent)' : 'var(--t-muted)' }}
              >
                {label}
              </span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
