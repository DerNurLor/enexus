import type { Metadata, Viewport } from 'next'
import '../styles/globals.css'
import { Providers } from '@/components/Providers'
import { MobileNav } from '@/components/layout/MobileNav'
import { DesktopSidebar } from '@/components/layout/DesktopSidebar'

export const metadata: Metadata = {
  title: 'НЦФУ — Расписание',
  description: 'Расписание занятий, новости и личный кабинет студента НЦФУ',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'НЦФУ',
  },
}

export const viewport: Viewport = {
  themeColor: '#0a0a0a',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body>
        <Providers>
          {/* Desktop: sidebar layout */}
          <div className="hidden lg:flex min-h-screen">
            <DesktopSidebar />
            <main className="flex-1 ml-64 min-h-screen">
              <div className="max-w-4xl mx-auto px-8 py-8">
                {children}
              </div>
            </main>
          </div>

          {/* Mobile: full screen + bottom nav */}
          <div className="lg:hidden min-h-screen flex flex-col">
            <main className="flex-1 pb-nav overflow-y-auto">
              {children}
            </main>
            <MobileNav />
          </div>
        </Providers>
      </body>
    </html>
  )
}
