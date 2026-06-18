'use client'
import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen, RefreshCw, Trash2, CheckCircle, AlertCircle,
  Loader2, ChevronDown, ChevronUp, Eye, EyeOff, Sparkles, Download
} from 'lucide-react'
import { fetchEcampusOverview, clearEcampusCache } from '@/lib/ecampus'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/api/ecampus'

async function authedFetch(path: string, options: RequestInit = {}) {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Error ${res.status}`)
  }
  return res.json()
}

type ConnectStatus = 'idle' | 'solving_captcha' | 'connecting' | 'success' | 'captcha_failed' | 'error'

// Состояние переавторизации (когда сессия протухла)
type ReauthState =
  | 'idle'           // обычное состояние
  | 'checking'       // проверяем сессию
  | 'need_captcha'   // нужна капча от пользователя
  | 'submitting'     // отправляем капчу
  | 'done'

interface SyncStatus {
  connected:          boolean
  enabled:            boolean
  sync_status:        string | null
  error_msg:          string | null
  last_sync:          string | null
  courses_count:      number
  files_count:        number
  sync_progress:      number
  sync_done_terms:    number
  sync_total_terms:   number
  sync_loaded_term_ids?: number[]
  sync_courses_found: number
}

interface Props { token: string | null; tgAuthReady?: boolean }

export function ECampusSection({ token, tgAuthReady = true }: Props) {
  // ── Состояние формы первого подключения ───────────────────────────────────
  const [showForm,     setShowForm]     = useState(false)
  const [showData,     setShowData]     = useState(false)
  const [login,        setLogin]        = useState('')
  const [password,     setPassword]     = useState('')
  const [captcha,      setCaptcha]      = useState('')
  const [showPass,     setShowPass]     = useState(false)
  const [autoCaptcha,  setAutoCaptcha]  = useState(true)
  const [captchaImg,   setCaptchaImg]   = useState<string | null>(null)
  const [captchaLoad,  setCaptchaLoad]  = useState(false)
  const [connectStatus, setConnectStatus] = useState<ConnectStatus>('idle')
  const [errorMsg,     setErrorMsg]     = useState<string | null>(null)

  // ── Состояние переавторизации (сессия протухла) ───────────────────────────
  const [reauthState,  setReauthState]  = useState<ReauthState>('idle')
  const [reauthImg,    setReauthImg]    = useState<string | null>(null)
  const [reauthCaptcha, setReauthCaptcha] = useState('')
  const [reauthAutoCaptha, setReauthAutoCaptcha] = useState(true)
  const [reauthMsg,    setReauthMsg]    = useState<string | null>(null)
  const [syncCooldown, setSyncCooldown] = useState(false)

  const qc = useQueryClient()

  const { data: status } = useQuery<SyncStatus>({
    queryKey: ['ecampus-status'],
    queryFn:  () => authedFetch('/status'),
    enabled:  !!token,
    refetchInterval: (query) => {
      const d = query.state.data as SyncStatus | undefined
      return d?.sync_status === 'running' ? 2000 : 30000
    },
  })

  const { data: syncData } = useQuery({
    queryKey: ['ecampus-data'],
    queryFn:  fetchEcampusOverview,
    enabled:  !!token && status?.sync_status === 'ok',
  })

  const loadCaptcha = useCallback(async (forReauth = false) => {
    if (forReauth) {
      setCaptchaLoad(true)
      setReauthCaptcha('')
    } else {
      setCaptchaLoad(true)
      setCaptcha('')
    }
    try {
      const data = await authedFetch('/captcha')
      if (forReauth) setReauthImg(data.image)
      else setCaptchaImg(data.image)
    } catch {
      setErrorMsg('Не удалось загрузить капчу')
    } finally {
      setCaptchaLoad(false)
    }
  }, [])

  useEffect(() => {
    if (showForm && !autoCaptcha && !captchaImg) loadCaptcha()
  }, [showForm, autoCaptcha]) // eslint-disable-line react-hooks/exhaustive-deps

  // Detect server-confirmed running→ok transition to refresh grades data.
  // syncInitiated is set only AFTER POST /sync returns (not during optimistic update),
  // so we avoid the race where the immediate invalidateQueries call returns 'ok'
  // before the worker even picks up the task.
  const syncInitiated  = useRef(false)
  const syncWasRunning = useRef(false)
  useEffect(() => {
    const s = status?.sync_status
    if (!s) return
    if (syncInitiated.current && s === 'running') {
      syncWasRunning.current = true
    }
    if (syncWasRunning.current && s !== 'running') {
      syncWasRunning.current = false
      syncInitiated.current  = false
      qc.invalidateQueries({ queryKey: ['ecampus-data'] })
    }
  }, [status?.sync_status, qc])

  const disconnectMutation = useMutation({
    mutationFn: () => authedFetch('/disconnect', { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ecampus-status'] })
      qc.removeQueries({ queryKey: ['ecampus-data'] })
      clearEcampusCache()
      setReauthState('idle')
    },
  })

  // ── Первое подключение ────────────────────────────────────────────────────
  const handleConnect = useCallback(async () => {
    if (!login || !password) return
    setErrorMsg(null)
    try {
      if (autoCaptcha) {
        setConnectStatus('solving_captcha')
        try {
          await authedFetch('/connect', {
            method: 'POST',
            body: JSON.stringify({ login, password, auto_captcha: true }),
          })
          setConnectStatus('success')
          setShowForm(false); setLogin(''); setPassword('')
          qc.invalidateQueries({ queryKey: ['ecampus-status'] })
        } catch {
          setConnectStatus('captcha_failed')
          setAutoCaptcha(false)
          await loadCaptcha()
          setErrorMsg('Не удалось решить капчу автоматически. Введите вручную.')
        }
      } else {
        if (!captcha) return
        setConnectStatus('connecting')
        await authedFetch('/connect', {
          method: 'POST',
          body: JSON.stringify({ login, password, captcha_code: captcha, auto_captcha: false }),
        })
        setConnectStatus('success')
        setShowForm(false); setLogin(''); setPassword(''); setCaptcha(''); setCaptchaImg(null)
        qc.invalidateQueries({ queryKey: ['ecampus-status'] })
      }
    } catch (e: any) {
      setConnectStatus('error')
      setErrorMsg(e.message)
      if (!autoCaptcha) await loadCaptcha()
    }
  }, [login, password, captcha, autoCaptcha, loadCaptcha, qc])

  // ── Умная синхронизация ───────────────────────────────────────────────────
  const handleSync = useCallback(async () => {
    setReauthState('checking')
    setReauthMsg(null)
    // Optimistic update: immediately show running progress bar
    qc.setQueryData(['ecampus-status'], (old: any) =>
      old ? { ...old, sync_status: 'running', sync_progress: 1 } : old
    )
    try {
      const result = await authedFetch('/sync', { method: 'POST' })
      if (result.ok) {
        setReauthState('idle')
        qc.invalidateQueries({ queryKey: ['ecampus-status'] })
        syncInitiated.current = true
        authedFetch('/reconfirm', { method: 'POST' }).catch(() => {})
        // КД 60 секунд
        setSyncCooldown(true)
        setTimeout(() => setSyncCooldown(false), 60_000)
        return
      }
      if (result.session_expired) {
        // Нужна капча от пользователя
        setReauthImg(result.captcha_image || null)
        setReauthMsg(result.message || 'Сессия истекла. Введите капчу.')
        setReauthState('need_captcha')
        if (!result.captcha_image) await loadCaptcha(true)
      }
    } catch (e: any) {
      setReauthState('idle')
      // 409 = уже запущена, игнорируем
      if (!e.message?.includes('409')) {
        setReauthMsg(e.message)
      }
    }
  }, [qc, loadCaptcha])

  // ── Переавторизация с капчей ──────────────────────────────────────────────
  const handleReauth = useCallback(async () => {
    setReauthState('submitting')
    setReauthMsg(null)
    try {
      const result = await authedFetch('/reauth', {
        method: 'POST',
        body: JSON.stringify({
          login: '',
          password: '',
          captcha_code: reauthAutoCaptha ? '' : reauthCaptcha,
          auto_captcha: reauthAutoCaptha,
        }),
      })
      if (result.ok) {
        setReauthState('done')
        setReauthImg(null)
        setReauthCaptcha('')
        qc.invalidateQueries({ queryKey: ['ecampus-status'] })
        setTimeout(() => setReauthState('idle'), 1500)
      } else if (result.session_expired) {
        // Неверная капча — показываем новую
        setReauthImg(result.captcha_image || null)
        setReauthMsg(result.message || 'Неверная капча. Попробуйте снова.')
        setReauthCaptcha('')
        setReauthState('need_captcha')
        if (!result.captcha_image) await loadCaptcha(true)
      }
    } catch (e: any) {
      setReauthMsg(e.message)
      setReauthState('need_captcha')
    }
  }, [reauthCaptcha, reauthAutoCaptha, qc, loadCaptcha])

  // Пока токен не инициализирован (плохая сеть) — показываем skeleton, не прячем секцию
  if (!token) {
    if (!tgAuthReady) {
      return (
        <div className="mt-4 rounded-2xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <div className="px-4 py-3 flex items-center gap-2">
            <div className="h-4 w-32 rounded skeleton" />
          </div>
          <div className="px-4 pb-3 flex flex-col gap-2">
            <div className="h-3 w-48 rounded skeleton" />
            <div className="h-8 w-full rounded-xl skeleton" />
          </div>
        </div>
      )
    }
    return null
  }

  const isRunning    = status?.sync_status === 'running'
  const isPending    = connectStatus === 'solving_captcha' || connectStatus === 'connecting'
  const canSubmit    = login && password && !isPending && (autoCaptcha || captcha)
  const isChecking   = reauthState === 'checking' || reauthState === 'submitting'
  // Вынесено ДО JSX чтобы избежать TypeScript type-narrowing внутри условных блоков
  const isSubmitting = (reauthState as string) === 'submitting'

  const statusLabel = {
    idle:            '',
    solving_captcha: 'Решаю капчу...',
    connecting:      'Подключение...',
    success:         'Готово',
    captcha_failed:  'Введите капчу вручную',
    error:           '',
  }[connectStatus]

  const progress     = status?.sync_progress ?? 0
  const doneTerm     = status?.sync_done_terms ?? 0
  const totalTerms   = status?.sync_total_terms ?? 0
  const coursesFound = status?.sync_courses_found ?? 0

  return (
    <div className="card px-5 py-4 mb-4">
      {/* Заголовок */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <BookOpen size={15} style={{ color: 'var(--accent)' }} />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>
            eCampus СКФУ
          </span>
        </div>
        {status?.connected && (
          <div className="flex items-center gap-1">
            {isRunning   && <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--accent)' }}><Loader2 size={10} className="animate-spin" />Синхронизация...</span>}
            {isChecking  && <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--t-muted)' }}><Loader2 size={10} className="animate-spin" />Проверяем...</span>}
            {status.sync_status === 'ok'    && reauthState === 'idle' && <span className="flex items-center gap-1 text-[10px]" style={{ color: '#4ade80' }}><CheckCircle size={10} />Готово</span>}
            {status.sync_status === 'error' && reauthState === 'idle' && <span className="flex items-center gap-1 text-[10px]" style={{ color: '#ef4444' }}><AlertCircle size={10} />Ошибка</span>}
            {reauthState === 'done' && <span className="flex items-center gap-1 text-[10px]" style={{ color: '#4ade80' }}><CheckCircle size={10} />Сессия обновлена</span>}
          </div>
        )}
      </div>

      {/* Прогресс синхронизации */}
      {isRunning && (
        <div className="mb-3">
          <div className="h-1.5 rounded-full overflow-hidden mb-1.5" style={{ background: 'var(--border)' }}>
            <div className="h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.max(5, progress)}%`, background: 'var(--accent)' }} />
          </div>
          <div className="flex justify-between text-[10px]" style={{ color: 'var(--t-muted)' }}>
            <span>{totalTerms > 0 ? `Семестр ${doneTerm} из ${totalTerms}` : 'Начало синхронизации...'}</span>
            {coursesFound > 0 && <span>{coursesFound} предметов найдено</span>}
          </div>
        </div>
      )}

      {/* Не подключено */}
      {!status?.connected && !showForm && (
        <div className="flex items-center justify-between">
          <p className="text-xs" style={{ color: 'var(--t-muted)' }}>Оценки, предметы и материалы</p>
          <button onClick={() => { setShowForm(true); setConnectStatus('idle'); setErrorMsg(null) }}
            className="shrink-0 ml-3 px-3 py-1.5 rounded-lg text-xs font-semibold"
            style={{ background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}>
            Подключить
          </button>
        </div>
      )}

      {/* Форма первого подключения */}
      {showForm && (
        <div className="flex flex-col gap-3">
          <p className="text-xs" style={{ color: 'var(--t-muted)' }}>
            Данные хранятся зашифрованными. Логин и пароль от eCampus СКФУ.
          </p>
          <input type="text" placeholder="Логин" value={login}
            onChange={e => setLogin(e.target.value)}
            className="input-search text-sm" autoComplete="username" disabled={isPending} />
          <div className="relative">
            <input type={showPass ? 'text' : 'password'} placeholder="Пароль"
              value={password} onChange={e => setPassword(e.target.value)}
              className="input-search text-sm w-full pr-10" autoComplete="current-password" disabled={isPending} />
            <button type="button" onClick={() => setShowPass(!showPass)}
              className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--t-muted)' }}>
              {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>

          <AutoCaptchaToggle
            value={autoCaptcha} disabled={isPending || connectStatus === 'captcha_failed'}
            onChange={v => { setAutoCaptcha(v); if (!v && !captchaImg) loadCaptcha() }}
          />

          {(!autoCaptcha || connectStatus === 'captcha_failed') && (
            <CaptchaInput img={captchaImg} loading={captchaLoad} value={captcha}
              onChange={setCaptcha} onRefresh={() => loadCaptcha()} />
          )}

          {isPending && statusLabel && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <Loader2 size={13} className="animate-spin" style={{ color: 'var(--accent)' }} />
              <span className="text-xs" style={{ color: 'var(--t-secondary)' }}>{statusLabel}</span>
            </div>
          )}
          {connectStatus === 'captcha_failed' && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
              style={{ background: '#fbbf2410', border: '1px solid #fbbf2430' }}>
              <AlertCircle size={13} style={{ color: '#fbbf24' }} />
              <span className="text-xs" style={{ color: '#fbbf24' }}>Введите капчу вручную и повторите</span>
            </div>
          )}
          {errorMsg && connectStatus === 'error' && (
            <p className="text-xs px-3 py-2 rounded-lg"
              style={{ background: '#ef444415', color: '#ef4444', border: '1px solid #ef444425' }}>
              {errorMsg}
            </p>
          )}
          <div className="flex gap-2">
            <button onClick={handleConnect} disabled={!canSubmit}
              className="flex-1 py-2 rounded-xl text-xs font-semibold disabled:opacity-50"
              style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
              {isPending ? statusLabel : 'Войти'}
            </button>
            <button onClick={() => { setShowForm(false); setCaptchaImg(null); setConnectStatus('idle'); setErrorMsg(null) }}
              disabled={isPending}
              className="px-3 py-2 rounded-xl text-xs disabled:opacity-50"
              style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}>
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* ── Подключено ──────────────────────────────────────────────────── */}
      {status?.connected && !showForm && (
        <div className="flex flex-col gap-3">

          {/* Форма переавторизации (сессия протухла) */}
          {reauthState === 'need_captcha' && (
            <div className="flex flex-col gap-3 px-3 py-3 rounded-xl"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <p className="text-xs font-semibold" style={{ color: '#fbbf24' }}>
                Сессия eCampus истекла
              </p>
              {reauthMsg && (
                <p className="text-xs" style={{ color: 'var(--t-secondary)' }}>{reauthMsg}</p>
              )}

              {/* Переключатель авто-капчи для переавторизации */}
              <AutoCaptchaToggle
                value={reauthAutoCaptha}
                disabled={false}
                onChange={v => { setReauthAutoCaptcha(v); if (!v && !reauthImg) loadCaptcha(true) }}
              />

              {!reauthAutoCaptha && (
                <CaptchaInput
                  img={reauthImg}
                  loading={captchaLoad}
                  value={reauthCaptcha}
                  onChange={setReauthCaptcha}
                  onRefresh={() => loadCaptcha(true)}
                />
              )}

              <div className="flex gap-2">
                <button
                  onClick={handleReauth}
                  disabled={isSubmitting || (!reauthAutoCaptha && !reauthCaptcha)}
                  className="flex-1 py-2 rounded-xl text-xs font-semibold disabled:opacity-50"
                  style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
                  {isSubmitting
                    ? <span className="flex items-center justify-center gap-1.5"><Loader2 size={12} className="animate-spin" />Входим...</span>
                    : 'Обновить сессию'}
                </button>
                <button onClick={() => { setReauthState('idle'); setReauthImg(null); setReauthMsg(null) }}
                  className="px-3 py-2 rounded-xl text-xs"
                  style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}>
                  Отмена
                </button>
              </div>
            </div>
          )}

          {/* Статистика */}
          {status.sync_status === 'ok' && reauthState !== 'need_captcha' && (
            <div className="flex gap-2">
              {[
                { value: status.courses_count, label: 'предметов' },
                { value: status.files_count,   label: 'файлов' },
                { value: status.last_sync
                  ? new Date(status.last_sync).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
                  : '—', label: 'обновлено' },
              ].map((item, i) => (
                <div key={i} className="flex-1 rounded-xl p-2.5 text-center" style={{ background: 'var(--surface)' }}>
                  <div className="text-sm font-bold" style={{ color: 'var(--accent)' }}>{item.value}</div>
                  <div className="text-[10px]" style={{ color: 'var(--t-muted)' }}>{item.label}</div>
                </div>
              ))}
            </div>
          )}

          {status.error_msg && reauthState !== 'need_captcha' && (
            <p className="text-xs px-3 py-2 rounded-lg"
              style={{ background: '#ef444415', color: '#ef4444', border: '1px solid #ef444425' }}>
              {status.error_msg}
            </p>
          )}

          {reauthMsg && reauthState === 'idle' && (
            <p className="text-xs px-3 py-2 rounded-lg"
              style={{ background: '#ef444415', color: '#ef4444', border: '1px solid #ef444425' }}>
              {reauthMsg}
            </p>
          )}

          {/* Список предметов */}
          {syncData?.courses?.length > 0 && reauthState !== 'need_captcha' && (
            <div>
              <button onClick={() => setShowData(!showData)}
                className="flex items-center gap-1 text-xs w-full text-left"
                style={{ color: 'var(--t-secondary)' }}>
                {showData ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {showData ? 'Скрыть предметы' : `Предметы (${syncData?.courses.length ?? 0})`}
              </button>
              {showData && (
                <div className="mt-2 flex flex-col gap-1 max-h-52 overflow-y-auto">
                  {syncData?.courses.map((c: any, i: number) => (
                    <div key={i} className="flex items-center px-3 py-2 rounded-lg"
                      style={{ background: 'var(--surface)' }}>
                      <p className="text-xs truncate flex-1" style={{ color: 'var(--t-primary)' }}>
                        {c.name || c.Name || `Предмет ${i + 1}`}
                      </p>
                      {c.term_name && (
                        <p className="text-[10px] ml-2 shrink-0" style={{ color: 'var(--t-muted)' }}>{c.term_name}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Кнопки действий */}
          {reauthState !== 'need_captcha' && (
            <div className="flex gap-2 pt-1 flex-wrap" style={{ borderTop: '1px solid var(--border)' }}>
              <button
                onClick={() => { if (!syncCooldown) handleSync() }}
                disabled={isRunning || isChecking || syncCooldown}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs disabled:opacity-50 hover:bg-white/5 transition-all"
                style={{ color: syncCooldown ? 'var(--t-muted)' : 'var(--accent)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}
                title={syncCooldown ? 'Подождите 60 сек' : 'Синхронизировать данные'}>
                <RefreshCw size={11} className={(isRunning || isChecking) ? 'animate-spin' : ''} />
                {syncCooldown ? 'Обновлено ✓' : 'Обновить'}
              </button>

              {status.sync_status === 'ok' && (
                <a href="#" onClick={async (e) => {
                  e.preventDefault()
                  const { useScheduleStore } = await import('@/lib/store')
                  const gid = useScheduleStore.getState().profile?.groupId
                  if (!gid) return
                  window.location.href = `${process.env.NEXT_PUBLIC_API_URL || ''}/api/schedules/group/${gid}/export.ics?weeks=8`
                }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs hover:bg-white/5"
                  style={{ color: 'var(--t-secondary)', border: '1px solid var(--border)' }}>
                  <Download size={11} />
                  .ics
                </a>
              )}

              <button onClick={() => { if (confirm('Удалить данные eCampus?')) disconnectMutation.mutate() }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs hover:bg-white/5"
                style={{ color: '#ef4444', border: '1px solid #ef444430' }}>
                <Trash2 size={11} />
                Отключить
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function AutoCaptchaToggle({
  value, disabled, onChange,
}: { value: boolean; disabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5 rounded-xl"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-center gap-2">
        <Sparkles size={13} style={{ color: value ? 'var(--accent)' : 'var(--t-muted)' }} />
        <span className="text-xs" style={{ color: value ? 'var(--t-primary)' : 'var(--t-muted)' }}>
          Автоматическая капча
        </span>
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input type="checkbox" className="sr-only peer" checked={value}
          onChange={e => onChange(e.target.checked)} disabled={disabled} />
        <div className="w-9 h-5 rounded-full transition-colors"
          style={{ background: value ? 'var(--accent)' : 'var(--border)' }} />
        <div className="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white transition-transform"
          style={{ transform: value ? 'translateX(16px)' : 'translateX(0)' }} />
      </label>
    </div>
  )
}

function CaptchaInput({
  img, loading, value, onChange, onRefresh,
}: {
  img: string | null; loading: boolean; value: string
  onChange: (v: string) => void; onRefresh: () => void
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        {loading
          ? <div className="w-32 h-12 rounded-lg animate-pulse" style={{ background: 'var(--border)' }} />
          : img
            ? <img src={img} alt="Капча" className="rounded-lg h-12 object-contain"
                style={{ background: '#fff', padding: 4 }} />
            : null
        }
        <button type="button" onClick={onRefresh} disabled={loading}
          className="p-2 rounded-lg hover:bg-white/5"
          style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>
      <input type="text" placeholder="Ответ на капчу"
        value={value} onChange={e => onChange(e.target.value)}
        className="input-search text-sm" autoComplete="off" />
    </div>
  )
}
