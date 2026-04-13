'use client'
import { usePathname } from 'next/navigation'
import { MobileNav }      from '@/components/layout/MobileNav'
import { DesktopSidebar } from '@/components/layout/DesktopSidebar'

const FULLSCREEN_ROUTES = ['/map']

export function ConditionalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
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
        <main className="flex-1 pb-nav overflow-y-auto">
          {children}
        </main>
        <MobileNav />
      </div>
    </>
  )
}
