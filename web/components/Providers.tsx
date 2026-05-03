'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { useScheduleStore } from '@/lib/store'
import { authenticateWithTelegram, setToken } from '@/lib/auth'

function ThemeApplier() {
  const { theme, accent_color } = useScheduleStore((s) => s.settings)

  useEffect(() => {
    const html = document.documentElement
    html.classList.remove('dark', 'light')
    if (theme === 'dark')  html.classList.add('dark')
    if (theme === 'light') html.classList.add('light')
  }, [theme])

  useEffect(() => {
    if (!accent_color) return
    document.documentElement.style.setProperty('--accent', accent_color)
    document.documentElement.style.setProperty('--cyan',   accent_color)
    const dimMatch = accent_color.match(/^#([0-9a-f]{6})$/i)
    if (dimMatch) {
      const r = parseInt(dimMatch[1].slice(0, 2), 16)
      const g = parseInt(dimMatch[1].slice(2, 4), 16)
      const b = parseInt(dimMatch[1].slice(4, 6), 16)
      const dim = `rgba(${r}, ${g}, ${b}, 0.12)`
      document.documentElement.style.setProperty('--accent-dim', dim)
      document.documentElement.style.setProperty('--cyan-dim',   dim)
    }
  }, [accent_color])

  return null
}

function TgAuthInit() {
  const {
    setTgUser, setAuthToken, setTgAuthReady, applyServerSettings, setFavorites,
  } = useScheduleStore()

  useEffect(() => {
    // Таймаут 10 сек — если сеть совсем плохая, не блокируем рендер
    const timeout = setTimeout(() => setTgAuthReady(true), 10000)

    async function tryAuth(attempt = 0): Promise<void> {
      try {
        const result = await authenticateWithTelegram()
        if (result) {
          setToken(result.token)
          setAuthToken(result.token)
          if (result.user) setTgUser(result.user)
          applyServerSettings(result.settings)
          if (result.favorites?.length > 0) setFavorites(result.favorites)
        }
        clearTimeout(timeout)
        setTgAuthReady(true)
      } catch {
        if (attempt === 0) {
          // Плохая сеть — ждём 2 сек и пробуем ещё раз
          setTimeout(() => tryAuth(1), 2000)
        } else {
          clearTimeout(timeout)
          setTgAuthReady(true)
        }
      }
    }

    tryAuth()
    return () => clearTimeout(timeout)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return null
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 1000 * 60 * 5, retry: 1 } },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      <TgAuthInit />
      <ThemeApplier />
      {children}
    </QueryClientProvider>
  )
}
