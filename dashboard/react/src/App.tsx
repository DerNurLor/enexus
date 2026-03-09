import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HelmetProvider, Helmet } from 'react-helmet-async'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'
import { api, extractError } from '@/api/client'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'
import { ToastRoot } from '@/components/common'
import { AuthGate } from '@/pages/AuthGate'
import { PanelOverview } from '@/pages/Overview'
import { PanelAnalytics } from '@/pages/Analytics'
import { PanelUsers } from '@/pages/Users'
import { PanelChats } from '@/pages/Chats'
import { PanelSupport } from '@/pages/Support'
import { PanelBroadcast } from '@/pages/Broadcast'
import { PanelRoles } from '@/pages/Roles'
import { PanelActivity, PanelErrors } from '@/pages/Logs'
import { PanelMongo } from '@/pages/Mongo'
import { PanelSettings } from '@/pages/Settings'
import type { PanelId } from '@/types'

// ── Query client (with sensible defaults for admin usage) ──────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
})

// ── Panel renderer ─────────────────────────────────────────────────────────

function PanelContent({ panel }: { panel: PanelId }) {
  switch (panel) {
    case 'overview':   return <PanelOverview />
    case 'analytics':  return <PanelAnalytics />
    case 'users':      return <PanelUsers />
    case 'chats':      return <PanelChats />
    case 'support':    return <PanelSupport />
    case 'broadcast':  return <PanelBroadcast />
    case 'roles':      return <PanelRoles />
    case 'activity':   return <PanelActivity />
    case 'errors':     return <PanelErrors />
    case 'mongo':      return <PanelMongo />
    case 'settings':   return <PanelSettings />
    default:           return <PanelOverview />
  }
}

// ── Main App ───────────────────────────────────────────────────────────────

function Dashboard() {
  const { token, user, setUser } = useAuthStore()
  const { panel, refreshKey } = useUIStore()

  // Load current user on mount if we have a token but no user
  useEffect(() => {
    if (token && !user) {
      api.getMe().then((d) => setUser(d.user)).catch(() => {})
    }
  }, [token])

  if (!token) return <AuthGate />

  return (
    <div className="layout">
      <Sidebar />
      <div className="main">
        <Topbar />
        <div className="content">
          <AnimatePresence mode="wait">
            <motion.div
              key={panel + '-' + refreshKey}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
              style={{ height: '100%' }}
            >
              <PanelContent panel={panel} />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
      <ToastRoot />
    </div>
  )
}

// ── Root export with providers ─────────────────────────────────────────────

export function App() {
  return (
    <HelmetProvider>
      <Helmet>
        <title>Admin · NCFU Dashboard</title>
        <meta name="robots" content="noindex, nofollow" />
        <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
      </Helmet>
      <QueryClientProvider client={queryClient}>
        <Dashboard />
      </QueryClientProvider>
    </HelmetProvider>
  )
}
