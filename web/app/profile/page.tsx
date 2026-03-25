'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  User, GraduationCap, BookOpen, Search, Check, ChevronRight,
  Edit2, X, Shield, Clock, Zap, Bell, SunMoon, Sun, Moon,
  MessageCircle, ChevronDown,
} from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { useScheduleStore } from '@/lib/store'
import type { UserRole } from '@/lib/store'
import { api } from '@/lib/api'
import { saveSettingsToServer, fetchQuota } from '@/lib/auth'
import { useRouter } from 'next/navigation'

type OnboardStep = 'choose-mode' | 'choose-role' | 'choose-group' | 'choose-teacher' | 'done'

// ── Debounce hook ─────────────────────────────────────────────────────────────
function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

// ── RBAC badge ────────────────────────────────────────────────────────────────
const ROLE_META: Record<string, { icon: string; label: string; color: string }> = {
  admin:     { icon: '🔴', label: 'Администратор', color: '#ef4444' },
  moderator: { icon: '🟠', label: 'Модератор',     color: '#f97316' },
  vip:       { icon: '🟡', label: 'VIP',           color: '#eab308' },
  beta:      { icon: '🔵', label: 'Бета-тестер',   color: '#3b82f6' },
  user:      { icon: '⚪', label: 'Пользователь',  color: '#8e8e93' },
}

function RoleBadge({ role }: { role: string }) {
  const meta = ROLE_META[role] ?? { icon: '⚫', label: role, color: '#8e8e93' }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
      style={{ background: `${meta.color}22`, color: meta.color, border: `1px solid ${meta.color}44` }}>
      {meta.icon} {meta.label}
    </span>
  )
}

// ── Quota bar ─────────────────────────────────────────────────────────────────
function QuotaSection({ token }: { token: string | null }) {
  const { data: quota, isLoading } = useQuery({
    queryKey: ['quota', token],
    queryFn:  fetchQuota,
    enabled:  !!token,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  if (!token) return null

  const pct = quota && quota.cap > 0 ? Math.min(quota.used / quota.cap * 100, 100) : 0
  const barColor = pct >= 100 ? '#ef4444' : pct >= 70 ? '#f97316' : 'var(--cyan)'

  return (
    <div className="card px-5 py-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>
          Лимит запросов к ИИ
        </p>
        {quota && (
          <span className="text-xs font-mono font-bold" style={{ color: barColor }}>
            {quota.used} / {quota.cap}
          </span>
        )}
      </div>
      {isLoading ? (
        <div className="h-2 rounded-full animate-pulse" style={{ background: 'var(--border)' }} />
      ) : quota ? (
        <>
          <div className="relative h-2 rounded-full overflow-hidden mb-2" style={{ background: 'var(--border)' }}>
            <div className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
              style={{ width: `${pct}%`, background: barColor }} />
          </div>
          <div className="flex justify-between text-[10px]" style={{ color: 'var(--t-muted)' }}>
            <span>{quota.exhausted ? '🔴 Лимит исчерпан' : `Осталось: ${quota.remaining}`}</span>
            <span>
              {quota.ttl_secs > 0
                ? `Сброс через ${Math.floor(quota.ttl_secs / 3600)}ч ${Math.floor((quota.ttl_secs % 3600) / 60)}м`
                : 'Лимит сброшен'}
            </span>
          </div>
        </>
      ) : (
        <p className="text-xs" style={{ color: 'var(--t-muted)' }}>Не удалось загрузить данные</p>
      )}
    </div>
  )
}

// ── Settings section ──────────────────────────────────────────────────────────
function ToggleRow({
  label, desc, checked, onChange,
}: { label: string; desc?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between py-3"
      style={{ borderBottom: '1px solid var(--border)' }}>
      <div>
        <p className="text-sm" style={{ color: 'var(--t-primary)' }}>{label}</p>
        {desc && <p className="text-[11px] mt-0.5" style={{ color: 'var(--t-muted)' }}>{desc}</p>}
      </div>
      <label className="relative inline-flex items-center cursor-pointer ml-4 shrink-0">
        <input type="checkbox" className="sr-only peer" checked={checked}
          onChange={e => onChange(e.target.checked)} />
        <div className="w-10 h-6 rounded-full transition-colors peer-checked:bg-cyan-400"
          style={{ background: checked ? 'var(--cyan)' : 'var(--border)' }} />
        <div className="absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform"
          style={{ transform: checked ? 'translateX(16px)' : 'translateX(0)' }} />
      </label>
    </div>
  )
}

type ThemeValue = 'auto' | 'light' | 'dark'

function SettingsSection() {
  const { settings, updateSettings, isAuthenticated } = useScheduleStore()

  // debounce сохранения на сервер
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const debouncedSave = useCallback((patch: Record<string, unknown>) => {
    if (!isAuthenticated) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      saveSettingsToServer(patch)
    }, 800)
  }, [isAuthenticated])

  const set = useCallback((key: keyof typeof settings, value: unknown) => {
    updateSettings({ [key]: value } as any)
    debouncedSave({ [key]: value })
  }, [updateSettings, debouncedSave])

  return (
    <div className="card px-5 py-4 mb-4">
      <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--t-muted)' }}>
        Настройки
      </p>

      <ToggleRow
        label="Неделя с понедельника"
        desc="Показывать расписание с пн, а не с сегодня"
        checked={!!settings.weekFromMonday}
        onChange={v => set('weekFromMonday', v)}
      />
      <ToggleRow
        label="24-часовой формат"
        checked={settings.time24h !== false}
        onChange={v => set('time24h', v)}
      />
      <ToggleRow
        label="Компактный вид"
        desc="Меньше деталей на карточке занятия"
        checked={!!settings.compact}
        onChange={v => set('compact', v)}
      />

      {/* Theme */}
      <div className="flex items-center justify-between py-3">
        <p className="text-sm" style={{ color: 'var(--t-primary)' }}>Тема оформления</p>
        <div className="flex gap-2">
          {(['auto', 'light', 'dark'] as ThemeValue[]).map(t => (
            <button key={t}
              onClick={() => set('theme', t)}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
              style={{
                background: settings.theme === t ? 'var(--cyan-dim)' : 'var(--border)',
                border: settings.theme === t ? '1.5px solid var(--cyan)' : '1.5px solid transparent',
              }}>
              {t === 'auto' ? <SunMoon size={14} style={{ color: settings.theme === t ? 'var(--cyan)' : 'var(--t-muted)' }} />
                : t === 'light' ? <Sun size={14} style={{ color: settings.theme === t ? 'var(--cyan)' : 'var(--t-muted)' }} />
                : <Moon size={14} style={{ color: settings.theme === t ? 'var(--cyan)' : 'var(--t-muted)' }} />}
            </button>
          ))}
        </div>
      </div>

      {!isAuthenticated && (
        <p className="text-[10px] mt-1" style={{ color: 'var(--t-muted)' }}>
          Настройки сохраняются локально. Войдите через Telegram для синхронизации.
        </p>
      )}
    </div>
  )
}

// ── Profile done state ────────────────────────────────────────────────────────
function ProfileDone({ onReset }: { onReset: () => void }) {
  const { profile, tgUser, authToken, isAuthenticated } = useScheduleStore()
  const router = useRouter()

  function goToSchedule() {
    if (!profile) { router.push('/schedule'); return }
    if (profile.role === 'student' && profile.groupId) {
      router.push(`/schedule?mode=group&id=${profile.groupId}&name=${encodeURIComponent(profile.groupName ?? '')}`)
    } else if (profile.role === 'teacher' && profile.teacherId) {
      router.push(`/schedule?mode=teacher&id=${profile.teacherId}&name=${encodeURIComponent(profile.teacherName ?? '')}`)
    } else {
      router.push('/schedule')
    }
  }

  const displayName = tgUser
    ? [tgUser.first_name, tgUser.last_name].filter(Boolean).join(' ')
    : (profile?.role === 'student' ? profile.groupName : profile?.teacherName) ?? '—'

  const subName = tgUser?.username ? `@${tgUser.username}` : (tgUser ? `tg:${tgUser.tg_id}` : null)

  return (
    <div className="animate-fade-up">
      {/* TG-профиль */}
      {tgUser && (
        <div className="card px-5 py-5 mb-4">
          <div className="flex items-center gap-4">
            {/* Аватар */}
            <div className="relative shrink-0">
              {tgUser.photo_url ? (
                <img src={tgUser.photo_url} alt={displayName}
                  className="w-16 h-16 rounded-full object-cover"
                  style={{ border: '2px solid rgba(92,225,230,0.4)' }}
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
              ) : (
                <div className="w-16 h-16 rounded-full flex items-center justify-center text-lg font-bold"
                  style={{ background: 'var(--cyan-dim)', border: '2px solid rgba(92,225,230,0.4)', color: 'var(--cyan)' }}>
                  {[tgUser.first_name?.[0], tgUser.last_name?.[0]].filter(Boolean).join('').toUpperCase() || '?'}
                </div>
              )}
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center"
                style={{ background: 'var(--cyan)' }}>
                <Check size={10} color="#000" />
              </div>
            </div>

            {/* Имя и username */}
            <div className="flex-1 min-w-0">
              <p className="text-base font-bold truncate" style={{ color: 'var(--t-primary)' }}>{displayName}</p>
              {subName && (
                <p className="text-sm truncate" style={{ color: 'var(--t-secondary)' }}>{subName}</p>
              )}
              <div className="flex flex-wrap gap-1 mt-1.5">
                {tgUser.roles.map(r => <RoleBadge key={r} role={r} />)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Профиль расписания */}
      {profile && (
        <div className="card px-5 py-4 mb-4">
          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--t-muted)' }}>
            Мои данные
          </p>
          <div className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--border)' }}>
            <span className="text-sm" style={{ color: 'var(--t-secondary)' }}>Роль</span>
            <span className="text-sm font-medium" style={{ color: 'var(--t-primary)' }}>
              {profile.role === 'student' ? 'Студент' : 'Преподаватель'}
            </span>
          </div>
          {profile.role === 'student' && (
            <div className="flex items-center justify-between py-2">
              <span className="text-sm" style={{ color: 'var(--t-secondary)' }}>Группа</span>
              <span className="text-sm font-bold" style={{ color: 'var(--cyan)' }}>{profile.groupName}</span>
            </div>
          )}
          {profile.role === 'teacher' && (
            <div className="flex items-center justify-between py-2">
              <span className="text-sm" style={{ color: 'var(--t-secondary)' }}>ФИО</span>
              <span className="text-sm font-bold" style={{ color: 'var(--cyan)' }}>{profile.teacherName}</span>
            </div>
          )}
        </div>
      )}

      {/* Квота */}
      <QuotaSection token={authToken} />

      {/* Настройки */}
      <SettingsSection />

      {/* Действия */}
      <div className="flex flex-col gap-3 mb-4">
        {profile && (
          <button onClick={goToSchedule}
            className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black transition-opacity hover:opacity-90"
            style={{ background: 'var(--cyan)' }}>
            Открыть моё расписание <ChevronRight size={16} />
          </button>
        )}
        <button onClick={onReset}
          className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-medium transition-colors hover:bg-white/5"
          style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
          <Edit2 size={15} /> Изменить профиль расписания
        </button>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ProfilePage() {
  const router = useRouter()
  const qc = useQueryClient()
  const {
    profile, profileComplete, setProfile, clearProfile,
    tgUser, authToken, isAuthenticated, tgAuthReady, settings,
  } = useScheduleStore()

  const [step, setStep] = useState<OnboardStep>('done')

  // DEBUG
  useEffect(() => {
    console.log('[Profile] tgAuthReady:', tgAuthReady, 'profileComplete:', profileComplete, 'tgUser:', !!tgUser, 'step:', step)
  })

  // Исправление: когда авторизация завершена (tgAuthReady=true), но нет ни профиля
  // ни TG-юзера, а step='done' (начальное значение) — переходим в choose-mode.
  // Без этого все условия рендера проваливаются и возвращается null (пустая страница).
  // Воспроизводится в браузере и electron у анонимного пользователя без профиля.
  useEffect(() => {
    if (tgAuthReady && step === 'done' && !profileComplete && !tgUser) {
      setStep('choose-mode')
    }
  }, [tgAuthReady, profileComplete, tgUser, step])
  const [selectedRole, setRole] = useState<UserRole>('student')
  const [query, setQuery]       = useState('')
  const [selectedGroupId, setSGId]      = useState<number | null>(null)
  const [selectedGroupName, setSGN]     = useState('')
  const [selectedTeacherId, setSTId]    = useState<number | null>(null)
  const [selectedTeacherName, setSTN]   = useState('')

  const debouncedQuery = useDebounce(query, 250)

  const { data: groupData } = useQuery({
    queryKey: ['search-groups-profile', debouncedQuery],
    queryFn:  () => api.searchGroups(debouncedQuery),
    enabled:  debouncedQuery.length >= 2 && step === 'choose-group',
  })

  const { data: teacherData } = useQuery({
    queryKey: ['search-teachers-profile', debouncedQuery],
    queryFn:  () => api.searchTeachers(debouncedQuery),
    enabled:  debouncedQuery.length >= 2 && step === 'choose-teacher',
  })

  // Синхронизируем профиль на сервер при сохранении
  async function handleSaveProfile() {
    let newProfile: typeof profile
    if (selectedRole === 'student' && selectedGroupId) {
      newProfile = { role: 'student', groupId: selectedGroupId, groupName: selectedGroupName, teacherId: null, teacherName: null }
    } else if (selectedRole === 'teacher' && selectedTeacherId) {
      newProfile = { role: 'teacher', groupId: null, groupName: null, teacherId: selectedTeacherId, teacherName: selectedTeacherName }
    } else {
      return
    }
    setProfile(newProfile)
    setStep('done')

    // Сохраняем на сервер если авторизован
    if (isAuthenticated) {
      await saveSettingsToServer({
        profile_role:         newProfile.role,
        profile_group_id:     newProfile.groupId,
        profile_group_name:   newProfile.groupName,
        profile_teacher_id:   newProfile.teacherId,
        profile_teacher_name: newProfile.teacherName,
      })
    }

    setTimeout(() => router.push('/schedule'), 300)
  }

  function resetForm() {
    clearProfile()
    setStep('choose-mode')
    setQuery('')
    setSGId(null); setSGN('')
    setSTId(null); setSTN('')

    // Очищаем профиль на сервере
    if (isAuthenticated) {
      saveSettingsToServer({
        profile_role:         null,
        profile_group_id:     null,
        profile_group_name:   null,
        profile_teacher_id:   null,
        profile_teacher_name: null,
      })
    }
  }

  // ── Ждём завершения авторизации ─────────────────────────────────────────────
  if (!tgAuthReady) {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Профиль" />
        <div className="flex flex-col gap-3 mt-4">
          {[1,2,3].map(i => (
            <div key={i} className="card px-5 py-4 h-20 animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  // ── DONE state ──────────────────────────────────────────────────────────────
  if ((profileComplete && profile && step === 'done') || (tgUser && step === 'done')) {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Профиль" />
        <ProfileDone onReset={resetForm} />
      </div>
    )
  }

  // ── No profile yet + TG user авторизован → показываем только TG-блок + кнопку настройки ──
  if (!profileComplete && tgUser && step === 'choose-mode') {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Профиль" />
        <div className="animate-fade-up">
          {/* TG-профиль */}
          <div className="card px-5 py-5 mb-4">
            <div className="flex items-center gap-4">
              <div className="relative shrink-0">
                {tgUser.photo_url ? (
                  <img src={tgUser.photo_url} alt=""
                    className="w-16 h-16 rounded-full object-cover"
                    style={{ border: '2px solid rgba(92,225,230,0.4)' }} />
                ) : (
                  <div className="w-16 h-16 rounded-full flex items-center justify-center text-lg font-bold"
                    style={{ background: 'var(--cyan-dim)', border: '2px solid rgba(92,225,230,0.4)', color: 'var(--cyan)' }}>
                    {[tgUser.first_name?.[0], tgUser.last_name?.[0]].filter(Boolean).join('').toUpperCase() || '?'}
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-base font-bold" style={{ color: 'var(--t-primary)' }}>
                  {[tgUser.first_name, tgUser.last_name].filter(Boolean).join(' ')}
                </p>
                {tgUser.username && (
                  <p className="text-sm" style={{ color: 'var(--t-secondary)' }}>@{tgUser.username}</p>
                )}
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {tgUser.roles.map(r => <RoleBadge key={r} role={r} />)}
                </div>
              </div>
            </div>
          </div>

          <QuotaSection token={authToken} />
          <SettingsSection />

          <div className="card px-5 py-5 mb-4">
            <p className="text-sm font-semibold mb-1" style={{ color: 'var(--t-primary)' }}>Расписание</p>
            <p className="text-xs mb-4" style={{ color: 'var(--t-secondary)' }}>
              Настройте профиль, чтобы расписание открывалось автоматически
            </p>
            <button
              onClick={() => setStep('choose-role')}
              className="w-full h-11 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black"
              style={{ background: 'var(--cyan)' }}>
              <GraduationCap size={16} /> Настроить профиль расписания
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── CHOOSE MODE (анонимный пользователь) ────────────────────────────────────
  if (step === 'choose-mode') {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Профиль" />
        <div className="flex flex-col items-center py-12 gap-6 animate-fade-up">
          <div className="w-20 h-20 rounded-full flex items-center justify-center"
            style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
            <User size={36} style={{ color: 'var(--t-muted)' }} />
          </div>
          <div className="text-center">
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--t-primary)' }}>Привет!</h2>
            <p className="text-sm max-w-xs leading-relaxed" style={{ color: 'var(--t-secondary)' }}>
              Настройте профиль, чтобы расписание открывалось автоматически при запуске
            </p>
          </div>
          <div className="w-full max-w-xs flex flex-col gap-3">
            <button onClick={() => setStep('choose-role')}
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black transition-opacity hover:opacity-90"
              style={{ background: 'var(--cyan)' }}>
              <GraduationCap size={16} /> Настроить профиль
            </button>
            <button onClick={() => router.push('/schedule')}
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-medium transition-colors hover:bg-white/5"
              style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
              Без профиля
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── CHOOSE ROLE ─────────────────────────────────────────────────────────────
  if (step === 'choose-role') {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Кто вы?" />
        <div className="animate-fade-up">
          <p className="text-sm mb-6" style={{ color: 'var(--t-secondary)' }}>Выберите вашу роль</p>
          <div className="grid grid-cols-2 gap-3 mb-6">
            {([
              { role: 'student' as UserRole, label: 'Студент',        icon: GraduationCap, desc: 'Расписание группы' },
              { role: 'teacher' as UserRole, label: 'Преподаватель',  icon: BookOpen,       desc: 'Расписание по ФИО' },
            ]).map(({ role, label, icon: Icon, desc }) => (
              <button key={role} onClick={() => setRole(role)}
                className="card p-4 flex flex-col items-center gap-2 transition-all duration-200"
                style={{
                  border: selectedRole === role ? '2px solid var(--cyan)' : '1px solid var(--border)',
                  background: selectedRole === role ? 'var(--cyan-dim)' : 'var(--card)',
                }}>
                <Icon size={28} style={{ color: selectedRole === role ? 'var(--cyan)' : 'var(--t-secondary)' }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>{label}</span>
                <span className="text-[10px]" style={{ color: 'var(--t-muted)' }}>{desc}</span>
              </button>
            ))}
          </div>
          <button
            onClick={() => setStep(selectedRole === 'student' ? 'choose-group' : 'choose-teacher')}
            className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black"
            style={{ background: 'var(--cyan)' }}>
            Далее <ChevronRight size={16} />
          </button>
        </div>
      </div>
    )
  }

  // ── CHOOSE GROUP ─────────────────────────────────────────────────────────────
  if (step === 'choose-group') {
    const groups = groupData?.groups ?? []
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Ваша группа" />
        <div className="animate-fade-up">
          <p className="text-sm mb-4" style={{ color: 'var(--t-secondary)' }}>Введите название группы</p>
          <div className="relative mb-4">
            <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: 'var(--t-muted)' }} />
            <input autoFocus placeholder="напр. ИС-21"
              value={query}
              onChange={e => { setQuery(e.target.value); setSGId(null) }}
              className="input-search pl-10 pr-10"
            />
            {query && (
              <button className="absolute right-3 top-1/2 -translate-y-1/2"
                onClick={() => { setQuery(''); setSGId(null) }}>
                <X size={13} style={{ color: 'var(--t-muted)' }} />
              </button>
            )}
          </div>
          {groups.length > 0 && (
            <div className="card overflow-hidden mb-4">
              {groups.slice(0, 8).map((g, idx) => (
                <button key={g.group_id}
                  onClick={() => { setSGId(g.group_id); setSGN(g.name); setQuery(g.name) }}
                  className="w-full text-left px-4 py-3 transition-colors hover:bg-white/5 flex items-center justify-between"
                  style={{
                    background: selectedGroupId === g.group_id ? 'var(--cyan-dim)' : undefined,
                    borderBottom: idx < groups.length - 1 ? '1px solid var(--border)' : undefined,
                  }}>
                  <div>
                    <p className="text-sm font-semibold"
                      style={{ color: selectedGroupId === g.group_id ? 'var(--cyan)' : 'var(--t-primary)' }}>
                      {g.name}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--t-muted)' }}>
                      {g.speciality_name} · {g.course} курс
                    </p>
                  </div>
                  {selectedGroupId === g.group_id && <Check size={15} style={{ color: 'var(--cyan)' }} />}
                </button>
              ))}
            </div>
          )}
          <button disabled={!selectedGroupId} onClick={handleSaveProfile}
            className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black"
            style={{
              background: selectedGroupId ? 'var(--cyan)' : 'rgba(92,225,230,0.3)',
              cursor: selectedGroupId ? 'pointer' : 'not-allowed',
            }}>
            <Check size={16} />
            {selectedGroupId ? `Выбрать ${selectedGroupName}` : 'Выберите группу'}
          </button>
        </div>
      </div>
    )
  }

  // ── CHOOSE TEACHER ───────────────────────────────────────────────────────────
  if (step === 'choose-teacher') {
    const teachers = teacherData?.teachers ?? []
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Ваше ФИО" />
        <div className="animate-fade-up">
          <p className="text-sm mb-4" style={{ color: 'var(--t-secondary)' }}>Введите фамилию или ФИО</p>
          <div className="relative mb-4">
            <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: 'var(--t-muted)' }} />
            <input autoFocus placeholder="напр. Иванов И.И."
              value={query}
              onChange={e => { setQuery(e.target.value); setSTId(null) }}
              className="input-search pl-10 pr-10"
            />
            {query && (
              <button className="absolute right-3 top-1/2 -translate-y-1/2"
                onClick={() => { setQuery(''); setSTId(null) }}>
                <X size={13} style={{ color: 'var(--t-muted)' }} />
              </button>
            )}
          </div>
          {teachers.length > 0 && (
            <div className="card overflow-hidden mb-4">
              {teachers.slice(0, 8).map((t, idx) => (
                <button key={t.teacher_id}
                  onClick={() => { setSTId(t.teacher_id); setSTN(t.full_name); setQuery(t.full_name) }}
                  className="w-full text-left px-4 py-3 transition-colors hover:bg-white/5 flex items-center justify-between"
                  style={{
                    background: selectedTeacherId === t.teacher_id ? 'var(--cyan-dim)' : undefined,
                    borderBottom: idx < teachers.length - 1 ? '1px solid var(--border)' : undefined,
                  }}>
                  <div>
                    <p className="text-sm font-semibold"
                      style={{ color: selectedTeacherId === t.teacher_id ? 'var(--cyan)' : 'var(--t-primary)' }}>
                      {t.full_name}
                    </p>
                    {t.subjects.length > 0 && (
                      <p className="text-xs mt-0.5" style={{ color: 'var(--t-muted)' }}>
                        {t.subjects.slice(0, 2).join(', ')}
                      </p>
                    )}
                  </div>
                  {selectedTeacherId === t.teacher_id && <Check size={15} style={{ color: 'var(--cyan)' }} />}
                </button>
              ))}
            </div>
          )}
          <button disabled={!selectedTeacherId} onClick={handleSaveProfile}
            className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black"
            style={{
              background: selectedTeacherId ? 'var(--cyan)' : 'rgba(92,225,230,0.3)',
              cursor: selectedTeacherId ? 'pointer' : 'not-allowed',
            }}>
            <Check size={16} />
            {selectedTeacherId ? `Выбрать ${selectedTeacherName}` : 'Выберите преподавателя'}
          </button>
        </div>
      </div>
    )
  }

  return null
}
