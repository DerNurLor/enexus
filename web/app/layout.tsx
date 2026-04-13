import type { Metadata, Viewport } from 'next'
import '../styles/globals.css'
import { Providers }          from '@/components/Providers'
import { ConditionalLayout }  from '@/components/layout/ConditionalLayout'

export const metadata: Metadata = {
  title: 'НЦФУ — Расписание',
  description: 'Расписание занятий, новости и личный кабинет студента НЦФУ',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'black-translucent', title: 'НЦФУ' },
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

const themeScript = `(function(){try{var raw=localStorage.getItem('ncfu-schedule');var theme='auto';if(raw){var s=JSON.parse(raw);theme=(s&&s.state&&s.state.settings&&s.state.settings.theme)||'auto';}var html=document.documentElement;html.classList.remove('dark','light');if(theme==='dark')html.classList.add('dark');if(theme==='light')html.classList.add('light');}catch(e){}})();`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <script src="https://telegram.org/js/telegram-web-app.js" />
      </head>
      <body>
        <Providers>
          <ConditionalLayout>
            {children}
          </ConditionalLayout>
        </Providers>
      </body>
    </html>
  )
}
