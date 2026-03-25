'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { useScheduleStore } from '@/lib/store'
import {
  authenticateWithTelegram,
  setToken,
} from '@/lib/auth'

function TgAuthInit() {
  const {
    setTgUser,
    setAuthToken,
    setTgAuthReady,
    applyServerSettings,
    setFavorites,
  } = useScheduleStore()

  useEffect(() => {
    // Гарантируем разблокировку страницы даже если fetch завис
    const timeout = setTimeout(() => {
      setTgAuthReady(true)
    }, 5000)

    authenticateWithTelegram()
      .then((result) => {
        if (result) {
          setToken(result.token)
          setAuthToken(result.token)
          setTgUser(result.user)
          applyServerSettings(result.settings)
          if (result.favorites.length > 0) setFavorites(result.favorites)
        }
      })
      .catch(() => {
        // Ошибка авторизации — продолжаем в анонимном режиме
      })
      .finally(() => {
        clearTimeout(timeout)
        setTgAuthReady(true)
      })

    return () => clearTimeout(timeout)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return null
}

/** Применяет тему к <html>: class="dark" | class="light" | ничего (auto) */
function ThemeApplier() {
  const theme = useScheduleStore((s) => s.settings.theme)

  useEffect(() => {
    const html = document.documentElement
    html.classList.remove('dark', 'light')
    if (theme === 'dark')  html.classList.add('dark')
    if (theme === 'light') html.classList.add('light')
    // 'auto' — классов нет, работает @media prefers-color-scheme
  }, [theme])

  return null
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5,
        retry: 1,
      },
    },
  }))
  return (
    <QueryClientProvider client={queryClient}>
      <TgAuthInit />
      <ThemeApplier />
      {children}
    </QueryClientProvider>
  )
}
