'use client'
import type { ReactNode } from 'react'
import { useGestures } from '@/hooks/useGestures'
import { useRouter } from 'next/navigation'
import { usePathname } from 'next/navigation'
import { MobileNav }       from '@/components/layout/MobileNav'
import { PWAInstallBanner } from '@/components/ui/PWAInstallBanner'
import { DesktopSidebar }  from '@/components/layout/DesktopSidebar'

const FULLSCREEN_ROUTES = ['/map']

export function ConditionalLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router   = useRouter()

  // Свайп от левого края = предыдущая вкладка, от правого = следующая
  const NAV_ORDER = ['/schedule', '/map', '/ecampus', '/profile']
  const currentIdx = NAV_ORDER.findIndex(h => pathname === h || pathname.startsWith(h + '/'))

  const navGestures = useGestures({
    onEdgeSwipeLeft:  () => { if (currentIdx < NAV_ORDER.length - 1) router.push(NAV_ORDER[currentIdx + 1]) },
    onEdgeSwipeRight: () => { if (currentIdx > 0) router.push(NAV_ORDER[currentIdx - 1]) },
    edgeZone: 24,
  })
  const isMap = FULLSCREEN_ROUTES.some(
    r => pathname === r || pathname.startsWith(r + '/')
  )

  if (isMap) {
    return (
      <>
        {/* Desktop: sidebar занимает w-64, карта — остальное */}
        <div className="hidden lg:flex h-screen">
          {/* placeholder чтобы flex правильно считал место под fixed sidebar */}
          <div className="w-64 shrink-0" />
          <DesktopSidebar />
          {/* Карта — relative контейнер без overflow */}
          <div className="flex-1 relative min-w-0">
            {children}
          </div>
        </div>

        {/* Mobile: карта fullscreen без MobileNav — карта имеет собственный таббар */}
        <div className="lg:hidden relative" style={{ height: '100dvh' }}>
          {children}
        </div>
      </>
    )
  }

  return (
    <>
      <div className="hidden lg:flex min-h-screen">
        <DesktopSidebar />
        <main className="flex-1 ml-64 min-h-screen">
          <div className="max-w-4xl mx-auto px-8 py-8">
            {children}
          </div>
        </main>
      </div>
      <div className="lg:hidden min-h-screen flex flex-col">
        <main className="flex-1 pb-nav overflow-y-auto" {...navGestures}>
          {children}
        </main>
        <PWAInstallBanner />
        <MobileNav />
      </div>
    </>
  )
}
