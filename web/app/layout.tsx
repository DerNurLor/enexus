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
  themeColor: [
    { media: '(prefers-color-scheme: dark)',  color: '#0d0d0f' },
    { media: '(prefers-color-scheme: light)', color: '#f4f4f5' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

/**
 * FOUC-prevention: инлайн-скрипт запускается синхронно до первого paint.
 * Читает сохранённую тему из localStorage и применяет класс к <html>.
 * Если тема 'auto' или не задана — тёмная тема по умолчанию
 * (html:not(.dark):not(.light) + @media prefers-color-scheme в CSS).
 *
 * ВАЖНО: dangerouslySetInnerHTML + suppressHydrationWarning на <html> —
 * единственный надёжный способ избежать мигания в Next.js App Router.
 */
const themeScript = `
(function(){
  try {
    var raw = localStorage.getItem('ncfu-schedule');
    var theme = 'auto';
    if (raw) {
      var s = JSON.parse(raw);
      theme = (s && s.state && s.state.settings && s.state.settings.theme) || 'auto';
    }
    var html = document.documentElement;
    html.classList.remove('dark', 'light');
    if (theme === 'dark')  html.classList.add('dark');
    if (theme === 'light') html.classList.add('light');
    // 'auto' — без класса, CSS @media prefers-color-scheme управляет темой
  } catch(e) {}
})();
`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        {/* FOUC-prevention — должен быть первым скриптом, до любых стилей */}
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        {/* Telegram WebApp SDK */}
        <script src="https://telegram.org/js/telegram-web-app.js" />
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
