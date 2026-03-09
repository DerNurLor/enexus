import { create } from 'zustand'
import type { PanelId } from '@/types'

export type ToastType = 'ok' | 'err' | 'info'

export interface Toast {
  id: number
  msg: string
  type: ToastType
}

interface UIState {
  panel: PanelId
  setPanel: (p: PanelId) => void
  toasts: Toast[]
  showToast: (msg: string, type?: ToastType, ms?: number) => void
  removeToast: (id: number) => void
  refreshKey: number
  triggerRefresh: () => void
  sidebarOpen: boolean
  toggleSidebar: () => void
}

let _toastId = 0

export const useUIStore = create<UIState>((set, get) => ({
  panel: 'overview',
  setPanel: (p) => set({ panel: p }),

  toasts: [],
  showToast: (msg, type = 'info', ms = 3200) => {
    const id = ++_toastId
    set((s) => ({ toasts: [...s.toasts, { id, msg, type }] }))
    setTimeout(() => get().removeToast(id), ms)
  },
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  refreshKey: 0,
  triggerRefresh: () => set((s) => ({ refreshKey: s.refreshKey + 1 })),

  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}))

// Convenience toast helpers
export const toast = {
  ok: (msg: string) => useUIStore.getState().showToast(msg, 'ok'),
  err: (msg: string) => useUIStore.getState().showToast(msg, 'err'),
  info: (msg: string) => useUIStore.getState().showToast(msg, 'info'),
}
