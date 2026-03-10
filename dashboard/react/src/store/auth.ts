import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AdminUser } from '@/types'

interface AuthState {
  token: string
  user: AdminUser | null
  setToken: (token: string) => void
  setUser: (user: AdminUser) => void
  clearToken: () => void
  logout: () => void
}

// Bootstrap token injected by the backend on ?secret= param
const bootstrapToken = (window as Window & { __BOOTSTRAP_TOKEN__?: string }).__BOOTSTRAP_TOKEN__

// If bootstrap token present — clear stale localStorage immediately
if (bootstrapToken) {
  localStorage.removeItem('adm_auth')
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: bootstrapToken || '',
      user: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      clearToken: () => set({ token: '', user: null }),
      logout: () => {
        set({ token: '', user: null })
      },
    }),
    {
      name: 'adm_auth',
      partialize: (state) => ({ token: state.token }),
    }
  )
)
