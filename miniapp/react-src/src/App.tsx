import React, { useState, useEffect, useCallback } from 'react'
import { api, setToken } from './utils/api'
import { useToast } from './hooks/useToast'
import { useTheme } from './hooks/useTheme'
import { Toast } from './components/Toast'
import { SchedulePage } from './pages/SchedulePage'
import { RoomsPage } from './pages/RoomsPage'
import { FavoritesPage } from './pages/FavoritesPage'
import { ProfilePage } from './pages/ProfilePage'
import {
  IconCalendar, IconBuilding, IconStar, IconUser,
} from './components/Icons'
import type { User, Page, Settings, Favorite, SearchType } from './types'

interface AuthResponse {
  token: string
  user: User
}
interface FavoritesResponse { favorites: Favorite[] }
interface SettingsResponse { settings: Settings }

export default function App() {
  const [booted, setBooted] = useState(false)
  const [appVisible, setAppVisible] = useState(false)
  const [loaderHidden, setLoaderHidden] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [user, setUser] = useState<User | null>(null)
  const [page, setPage] = useState<Page>('schedule')
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [settings, setSettings] = useState<Settings>({ time24h: true })
  const { message: toastMsg, visible: toastVisible, toast } = useToast()
  useTheme((settings.theme as 'auto' | 'light' | 'dark') ?? 'auto')

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    tg?.ready()
    tg?.expand()

    const initData = tg?.initData ?? ''

    const boot = async () => {
      try {
        if (!initData) {
          // Dev mode
          // setUser({
          //   id: 'dev', tg_id: 0,
          //   first_name: 'Dev', last_name: 'User',
          //   username: 'devuser', display: 'Dev User',
          //   roles: ['user', 'beta'], permissions: ['beta_access'],
          //   is_blocked: false, is_beta: true, is_vip: false, is_admin: false,
          //   avatar: undefined,
          // })
          // setToken('dev')
          // toast('Dev mode — initData отсутствует')
          // revealApp()
          setErrorMsg('Приложение доступно только через Telegram.')
          return
        }

        const authData = await api<AuthResponse>('/miniapp/auth', {
          method: 'POST',
          body: JSON.stringify({ init_data: initData }),
        })
        setToken(authData.token)
        setUser(authData.user)

        const [favsData, settingsData] = await Promise.all([
          api<FavoritesResponse>('/miniapp/api/favorites').catch(() => ({ favorites: [] })),
          api<SettingsResponse>('/miniapp/api/settings').catch(() => ({ settings: {} })),
        ])
        setFavorites(favsData.favorites ?? [])
        setSettings({ time24h: true, ...settingsData.settings })

        revealApp()
      } catch (e) {
        setErrorMsg('Ошибка авторизации. Попробуйте открыть приложение заново.')
      }
    }

    boot()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function revealApp() {
    setBooted(true)
    setTimeout(() => {
      setAppVisible(true)
      setTimeout(() => setLoaderHidden(true), 400)
    }, 120)
  }

  // Handle navigation — haptic + page switch
  const navigate = useCallback((p: Page) => {
    setPage(p)
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
  }, [])

  // Favorites management
  const addFav = useCallback(async (type: SearchType, id: string, name: string) => {
    if (favorites.some(f => f.type === type && f.id === id)) {
      toast('Уже в избранном'); return
    }
    try {
      const data = await api<FavoritesResponse>('/miniapp/api/favorites', {
        method: 'POST',
        body: JSON.stringify({ type, id, label: name }),
      })
      setFavorites(data.favorites ?? favorites)
      toast('Добавлено в избранное ★')
    } catch { toast('Ошибка сохранения') }
  }, [favorites, toast])

  const deleteFav = useCallback(async (fav: Favorite) => {
    try {
      const favId = encodeURIComponent(`${fav.type}:${fav.id}`)
      const data = await api<FavoritesResponse>(`/miniapp/api/favorites/${favId}`, {
        method: 'DELETE',
      })
      setFavorites(data.favorites ?? favorites)
    } catch { toast('Ошибка удаления') }
  }, [favorites, toast])

  const loadFav = useCallback((fav: Favorite) => {
    navigate('schedule')
    // Signal SchedulePage to open this favorite
    const evt = new CustomEvent('loadFavorite', { detail: fav })
    window.dispatchEvent(evt)
  }, [navigate])

  // Settings update
  const updateSetting = useCallback((key: keyof Settings, value: unknown) => {
    setSettings(prev => {
      const next = { ...prev, [key]: value }
      api('/miniapp/api/settings', {
        method: 'POST',
        body: JSON.stringify({ [key]: value }),
      }).catch(() => {})
      return next
    })
  }, [])

  // Room open from rooms page
  const handleRoomOpen = useCallback((room: string) => {
    navigate('schedule')
    setTimeout(() => {
      const evt = new CustomEvent('openRoom', { detail: room })
      window.dispatchEvent(evt)
    }, 80)
  }, [navigate])


  // Listen to openRoom event — SchedulePage handles it via its own useEffect
  useEffect(() => {
    // No-op listener here; openRoom events are dispatched and SchedulePage handles them
  }, [])

  const initials = user
    ? ((user.first_name?.[0] ?? '') + (user.last_name?.[0] ?? '')).toUpperCase()
    : '?'

  const getRoleDotClass = () => {
    if (!user) return null
    if (user.is_admin) return 'admin'
    if (user.is_vip) return 'vip'
    if (user.is_beta) return 'beta'
    return null
  }

  const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
    {
      id: 'schedule',
      label: 'Расписание',
      icon: <IconCalendar size={20} />,
    },
    {
      id: 'rooms',
      label: 'Аудитории',
      icon: <IconBuilding size={20} />,
    },
    {
      id: 'favorites',
      label: 'Избранное',
      icon: <IconStar size={20} />,
    },
    {
      id: 'profile',
      label: 'Профиль',
      icon: <IconUser size={20} />,
    },
  ]

  return (
    <>
      {/* Loader */}
      <div className={`loader${loaderHidden ? ' hidden' : ''}`}>
        {errorMsg ? (
          <div style={{
            fontFamily: 'var(--display)',
            fontSize: 18,
            fontWeight: 700,
            color: 'var(--text-primary)',
            textAlign: 'center',
            padding: 24,
            maxWidth: 280,
            lineHeight: 1.4,
          }}>
            {errorMsg}
          </div>
        ) : (
            <>
              <div className="loader-logo">СКФУ</div>
              <div className="loader-ring" />
              <div className="loader-sub">Загрузка расписания…</div>
            </>
          )}
      </div>

      {/* App */}
      {booted && !errorMsg && (
        <div className={`app${appVisible ? ' visible' : ''}`}>
          {/* Header */}
          <header className="header">
            <div className="header-wordmark">
              <div className="header-title">СКФУ</div>
              <div className="header-sub">Расписание занятий</div>
            </div>
            <div
              className="header-avatar"
              onClick={() => navigate('profile')}
              role="button"
              tabIndex={0}
              aria-label="Профиль"
            >
              {user?.avatar
                ? <img src={user.avatar} alt="" onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                : initials
              }
              {getRoleDotClass() && (
                <div className={`role-dot ${getRoleDotClass()}`} />
              )}
            </div>
          </header>

          {/* Pages */}
          <main className="pages">
            <SchedulePage
              isActive={page === 'schedule'}
              settings={settings}
              favorites={favorites}
              onAddFav={addFav}
              toast={toast}
            />
            <RoomsPage
              isActive={page === 'rooms'}
              toast={toast}
              onRoomClick={handleRoomOpen}
            />
            <FavoritesPage
              isActive={page === 'favorites'}
              favorites={favorites}
              onDelete={deleteFav}
              onLoad={loadFav}
            />
            <ProfilePage
              isActive={page === 'profile'}
              user={user}
              settings={settings}
              onSettingChange={updateSetting}
              toast={toast}
            />
          </main>

          {/* Bottom nav */}
          <nav className="bottom-nav" aria-label="Основная навигация">
            {navItems.map(item => (
              <button
                key={item.id}
                className={`nav-btn${page === item.id ? ' active' : ''}`}
                onClick={() => navigate(item.id)}
                aria-current={page === item.id ? 'page' : undefined}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      )}

      <Toast message={toastMsg} visible={toastVisible} />
    </>
  )
}
