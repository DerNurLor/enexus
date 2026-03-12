'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { useScheduleStore } from '@/lib/store'
import {
  authenticateWithTelegram,
  setToken,
  isTelegramWebApp,
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
    if (!isTelegramWebApp()) {
      // Обычный браузер — пробуем тихий рефреш через saved refresh token
      // authenticateWithTelegram справится с этим сам (нет initData → _silentRefresh)
      authenticateWithTelegram().then((result) => {
        if (result) {
          setToken(result.token)
          setAuthToken(result.token)
          setTgUser(result.user)
          applyServerSettings(result.settings)
          if (result.favorites.length > 0) setFavorites(result.favorites)
        }
        setTgAuthReady(true)
      })
      return
    }

    // TG Mini App: full auth
    authenticateWithTelegram().then((result) => {
      if (result) {
        setToken(result.token)
        setAuthToken(result.token)
        setTgUser(result.user)
        applyServerSettings(result.settings)
        if (result.favorites.length > 0) setFavorites(result.favorites)
      }
      setTgAuthReady(true)
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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
      {children}
    </QueryClientProvider>
  )
}
