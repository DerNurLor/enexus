'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { CalendarDays, BookOpen, User, Map } from 'lucide-react'
import { useScheduleStore } from '@/lib/store'
import { useT } from '@/lib/i18n'

export function MobileNav() {
  const pathname      = usePathname()
  const newGradesCount = useScheduleStore((s) => s.newGradesCount)
  const profile        = useScheduleStore((s) => s.profile)
  const isTeacher      = profile?.role === 'teacher'
  const { t } = useT()

  const NAV_ITEMS = [
    { href: '/schedule', label: t('nav.schedule'), icon: CalendarDays },
    { href: '/map',      label: t('nav.map'),       icon: Map          },
    isTeacher
      ? { href: '/teacher', label: t('nav.lessons_short'), icon: BookOpen }
      : { href: '/ecampus', label: t('nav.subjects'), icon: BookOpen },
    { href: '/profile',  label: t('nav.profile'),     icon: User         },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 lg:hidden"
      style={{ background: 'var(--card)', borderTop: '1px solid var(--border)', paddingBottom: 'env(safe-area-inset-bottom)' }}>
      <div className="flex items-stretch">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive  = pathname === href || pathname.startsWith(href + '/')
          const badge     = href === '/ecampus' && newGradesCount > 0 ? newGradesCount : 0

          return (
            <Link key={href} href={href}
              className="flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[56px] relative"
              style={{ color: isActive ? 'var(--accent)' : 'var(--t-muted)' }}>
              <div className="relative">
                <Icon size={22} strokeWidth={isActive ? 2.2 : 1.6}
                  style={{ color: isActive ? 'var(--accent)' : 'var(--t-muted)' }} />
                {badge > 0 && (
                  <span className="absolute -top-1.5 -right-2 min-w-[16px] h-4 flex items-center justify-center px-1 text-[9px] font-bold rounded-full"
                    style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
                    {badge > 9 ? '9+' : badge}
                  </span>
                )}
              </div>
              <span className="text-[10px] font-medium leading-none"
                style={{ color: isActive ? 'var(--accent)' : 'var(--t-muted)' }}>
                {label}
              </span>
              {/* Active indicator dot */}
              {isActive && (
                <span className="absolute bottom-1.5 w-1 h-1 rounded-full"
                  style={{ background: 'var(--accent)' }} />
              )}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
