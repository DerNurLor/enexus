import { Icon } from '@/components/common/Icons'
import { Spinner } from '@/components/common'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'
import { api } from '@/api/client'
import { toast } from '@/store/ui'
import { extractError } from '@/api/client'

const PANEL_TITLES: Record<string, string> = {
  overview:  'Обзор',
  analytics: 'Аналитика',
  users:     'Пользователи',
  chats:     'Чаты',
  support:   'Поддержка',
  broadcast: 'Рассылка',
  roles:     'Роли и права',
  activity:  'Журнал активности',
  errors:    'Журнал ошибок',
  mongo:     'MongoDB Viewer',
  settings:  'Настройки системы',
}

export function Topbar() {
  const user = useAuthStore((s) => s.user)
  const { panel, refreshKey, triggerRefresh } = useUIStore()
  const refreshing = useUIStore((s) => s.toasts).length === 0

  async function handleRefresh() {
    triggerRefresh()
  }

  async function invalidateCache() {
    try {
      await api.invalidateCache()
      toast.ok('Кэш сброшен')
    } catch (e) {
      toast.err(extractError(e))
    }
  }

  return (
    <div className="topbar">
      <div className="topbar-title">{PANEL_TITLES[panel] ?? panel}</div>
      <div className="topbar-actions">
        <button className="btn btn-ghost" onClick={handleRefresh} title="Обновить">
          <Icon.refresh />
          <span>Обновить</span>
        </button>
        {(panel === 'overview' || panel === 'analytics') && (
          <button className="btn btn-ghost" onClick={invalidateCache} title="Сбросить кэш Redis">
            Сбросить кэш
          </button>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 8px', background: 'var(--ink-20)', borderRadius: 'var(--rad)', border: '1px solid var(--line)' }}>
          <span className="dot dot-ok" />
          <span style={{ fontSize: 9, color: 'var(--t-60)' }}>{user?.display ?? '—'}</span>
        </div>
      </div>
    </div>
  )
}
