import { motion } from 'framer-motion'
import { Icon } from '@/components/common/Icons'
import { UserAvatar } from '@/components/common'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'
import type { PanelId, NavItem } from '@/types'

const NAV_ITEMS: NavItem[] = [
  { id: 'overview',   label: 'Обзор',        group: 'Главная' },
  { id: 'analytics',  label: 'Аналитика',    group: 'Главная' },
  { id: 'users',      label: 'Пользователи', group: 'Управление' },
  { id: 'chats',      label: 'Чаты',         group: 'Управление' },
  { id: 'support',    label: 'Поддержка',    group: 'Управление' },
  { id: 'broadcast',  label: 'Рассылка',     group: 'Управление' },
  { id: 'roles',      label: 'Роли',         group: 'Управление' },
  { id: 'activity',   label: 'Активность',   group: 'Логи' },
  { id: 'errors',     label: 'Ошибки',       group: 'Логи' },
  { id: 'mongo',      label: 'MongoDB',      group: 'Dev' },
  { id: 'settings',   label: 'Настройки',    group: 'Dev' },
]

const ICONS: Record<string, () => JSX.Element> = {
  overview:   Icon.overview,
  analytics:  Icon.analytics,
  users:      Icon.users,
  chats:      Icon.chats,
  support:    Icon.support,
  broadcast:  Icon.broadcast,
  roles:      Icon.roles,
  activity:   Icon.activity,
  errors:     Icon.errors,
  mongo:      Icon.mongo,
  settings:   Icon.settings,
}

export function Sidebar() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const panel = useUIStore((s) => s.panel)
  const setPanel = useUIStore((s) => s.setPanel)
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)

  const groups = NAV_ITEMS.reduce<Record<string, NavItem[]>>((acc, item) => {
    if (!acc[item.group]) acc[item.group] = []
    acc[item.group].push(item)
    return acc
  }, {})

  return (
    <motion.div
      className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}
      animate={{ width: sidebarOpen ? 200 : 48 }}
      transition={{ type: 'spring', damping: 28, stiffness: 260 }}
    >
      {/* Logo */}
      <div className="sidebar-logo" style={{ padding: sidebarOpen ? undefined : '20px 12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {sidebarOpen && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="sidebar-logo-title">NCFU</div>
              <div className="sidebar-logo-sub">Admin Dashboard</div>
            </motion.div>
          )}
          <button className="btn btn-ghost btn-icon" onClick={toggleSidebar} style={{ flexShrink: 0 }}>
            <Icon.menu />
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {Object.entries(groups).map(([group, items]) => (
          <div key={group}>
            {sidebarOpen && <div className="nav-group-label">{group}</div>}
            {items.map((item) => {
              const IconComp = ICONS[item.id] ?? Icon.settings
              return (
                <button
                  key={item.id}
                  className={`nav-item ${panel === item.id ? 'active' : ''}`}
                  onClick={() => setPanel(item.id as PanelId)}
                  title={!sidebarOpen ? item.label : undefined}
                  style={{ padding: sidebarOpen ? '7px 18px' : '7px 17px', justifyContent: sidebarOpen ? undefined : 'center' }}
                >
                  <span className="nav-item-icon"><IconComp /></span>
                  {sidebarOpen && (
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {item.label}
                    </motion.span>
                  )}
                  {sidebarOpen && item.badge != null && (
                    <span className="nav-badge live">{item.badge}</span>
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        {sidebarOpen ? (
          <div className="sidebar-user">
            <div className="sidebar-avatar">
              {user ? <UserAvatar user={user} size={24} /> : '?'}
            </div>
            <div className="sidebar-user-name">{user?.display ?? '—'}</div>
            <button className="btn btn-ghost btn-icon" onClick={logout} title="Выйти">
              <Icon.logout />
            </button>
          </div>
        ) : (
          <button className="btn btn-ghost btn-icon" onClick={logout} title="Выйти" style={{ width: '100%', justifyContent: 'center' }}>
            <Icon.logout />
          </button>
        )}
      </div>
    </motion.div>
  )
}
