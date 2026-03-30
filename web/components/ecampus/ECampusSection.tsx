'use client'
import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen, RefreshCw, Trash2, CheckCircle, AlertCircle,
  Loader2, ChevronDown, ChevronUp, Eye, EyeOff, Sparkles, Download
} from 'lucide-react'

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

type ConnectStatus =
  | 'idle'
  | 'solving_captcha'
  | 'connecting'
  | 'success'
  | 'captcha_failed'
  | 'error'

interface SyncStatus {
  connected:          boolean
  enabled:            boolean
  sync_status:        string | null
  error_msg:          string | null
  last_sync:          string | null
  courses_count:      number
  files_count:        number
  // Прогресс (добавлено в улучшении)
  sync_progress:      number
  sync_done_terms:    number
  sync_total_terms:   number
  sync_courses_found: number
}

interface Props { token: string | null }

export function ECampusSection({ token }: Props) {
  const [showForm,    setShowForm]    = useState(false)
  const [showData,    setShowData]    = useState(false)
  const [login,       setLogin]       = useState('')
  const [password,    setPassword]    = useState('')
  const [captcha,     setCaptcha]     = useState('')
  const [showPass,    setShowPass]    = useState(false)
  const [autoCaptcha, setAutoCaptcha] = useState(true)
  const [captchaImg,  setCaptchaImg]  = useState<string | null>(null)
  const [captchaLoad, setCaptchaLoad] = useState(false)
  const [connectStatus, setConnectStatus] = useState<ConnectStatus>('idle')
  const [errorMsg,    setErrorMsg]    = useState<string | null>(null)
  const qc = useQueryClient()

  // УЛУЧШЕНИЕ: refetchInterval адаптируется к состоянию синхронизации.
  // Во время синхронизации опрашиваем каждые 2 секунды для live-прогресса.
  // В остальное время — раз в 30 секунд.
  const { data: status } = useQuery<SyncStatus>({
    queryKey: ['ecampus-status'],
    queryFn:  () => authedFetch('/status'),
    enabled:  !!token,
    refetchInterval: (query) => {
      const data = query.state.data as SyncStatus | undefined
      return data?.sync_status === 'running' ? 2000 : 30000
    },
  })

  const { data: syncData } = useQuery({
    queryKey: ['ecampus-data'],
    queryFn:  () => authedFetch('/data'),
    enabled:  !!token && status?.sync_status === 'ok',
  })

  const loadCaptcha = useCallback(async () => {
    setCaptchaLoad(true)
    setCaptcha('')
    try {
      const data = await authedFetch('/captcha')
      setCaptchaImg(data.image)
    } catch {
      setErrorMsg('Не удалось загрузить капчу')
    } finally {
      setCaptchaLoad(false)
    }
  }, [])

  useEffect(() => {
    if (showForm && !autoCaptcha && !captchaImg) loadCaptcha()
  }, [showForm, autoCaptcha]) // eslint-disable-line react-hooks/exhaustive-deps

  const syncMutation = useMutation({
    mutationFn: () => authedFetch('/sync', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ecampus-status'] }),
  })

  const disconnectMutation = useMutation({
    mutationFn: () => authedFetch('/disconnect', { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ecampus-status'] })
      qc.removeQueries({ queryKey: ['ecampus-data'] })
    },
  })

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
        } catch (e: any) {
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

  if (!token) return null

  const isRunning  = status?.sync_status === 'running'
  const isPending  = connectStatus === 'solving_captcha' || connectStatus === 'connecting'
  const canSubmit  = login && password && !isPending && (autoCaptcha || captcha)

  const statusLabel = {
    idle:            '',
    solving_captcha: 'Решаю капчу...',
    connecting:      'Подключение...',
    success:         'Готово',
    captcha_failed:  'Введите капчу вручную',
    error:           '',
  }[connectStatus]

  // УЛУЧШЕНИЕ: вычисляем процент прогресса с защитой от деления на ноль
  const progress    = status?.sync_progress ?? 0
  const doneTerm    = status?.sync_done_terms ?? 0
  const totalTerms  = status?.sync_total_terms ?? 0
  const coursesFound = status?.sync_courses_found ?? 0

  return (
    <div className="card px-5 py-4 mb-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <BookOpen size={15} style={{ color: 'var(--cyan)' }} />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--t-muted)' }}>
            eCampus СКФУ
          </span>
        </div>
        {status?.connected && (
          <div className="flex items-center gap-1">
            {isRunning && <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--cyan)' }}><Loader2 size={10} className="animate-spin" />Синхронизация...</span>}
            {status.sync_status === 'ok' && <span className="flex items-center gap-1 text-[10px]" style={{ color: '#4ade80' }}><CheckCircle size={10} />Готово</span>}
            {status.sync_status === 'error' && <span className="flex items-center gap-1 text-[10px]" style={{ color: '#ef4444' }}><AlertCircle size={10} />Ошибка</span>}
          </div>
        )}
      </div>

      {/* УЛУЧШЕНИЕ: Прогресс-бар синхронизации в реальном времени */}
      {isRunning && (
        <div className="mb-3">
          <div className="h-1.5 rounded-full overflow-hidden mb-1.5" style={{ background: 'var(--border)' }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.max(5, progress)}%`, background: 'var(--cyan)' }}
            />
          </div>
          <div className="flex justify-between text-[10px]" style={{ color: 'var(--t-muted)' }}>
            <span>
              {totalTerms > 0
                ? `Семестр ${doneTerm} из ${totalTerms}`
                : 'Начало синхронизации...'}
            </span>
            {coursesFound > 0 && (
              <span>{coursesFound} предметов найдено</span>
            )}
          </div>
        </div>
      )}

      {/* Not connected */}
      {!status?.connected && !showForm && (
        <div className="flex items-center justify-between">
          <p className="text-xs" style={{ color: 'var(--t-muted)' }}>Оценки, предметы и материалы</p>
          <button onClick={() => { setShowForm(true); setConnectStatus('idle'); setErrorMsg(null) }}
            className="shrink-0 ml-3 px-3 py-1.5 rounded-lg text-xs font-semibold"
            style={{ background: 'var(--cyan-dim)', color: 'var(--cyan)', border: '1px solid var(--cyan)33' }}>
            Подключить
          </button>
        </div>
      )}

      {/* Connect form */}
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

          {connectStatus !== 'captcha_failed' && (
            <div className="flex items-center justify-between px-3 py-2.5 rounded-xl"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="flex items-center gap-2">
                <Sparkles size={13} style={{ color: autoCaptcha ? 'var(--cyan)' : 'var(--t-muted)' }} />
                <span className="text-xs" style={{ color: autoCaptcha ? 'var(--t-primary)' : 'var(--t-muted)' }}>
                  Автоматическая капча
                </span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" checked={autoCaptcha}
                  onChange={e => {
                    setAutoCaptcha(e.target.checked)
                    if (!e.target.checked && !captchaImg) loadCaptcha()
                  }} disabled={isPending} />
                <div className="w-9 h-5 rounded-full transition-colors"
                  style={{ background: autoCaptcha ? 'var(--cyan)' : 'var(--border)' }} />
                <div className="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                  style={{ transform: autoCaptcha ? 'translateX(16px)' : 'translateX(0)' }} />
              </label>
            </div>
          )}

          {(!autoCaptcha || connectStatus === 'captcha_failed') && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                {captchaLoad
                  ? <div className="w-32 h-12 rounded-lg animate-pulse" style={{ background: 'var(--border)' }} />
                  : captchaImg
                    ? <img src={captchaImg} alt="Капча" className="rounded-lg h-12 object-contain"
                        style={{ background: '#fff', padding: 4 }} />
                    : null
                }
                <button type="button" onClick={loadCaptcha} disabled={captchaLoad}
                  className="p-2 rounded-lg hover:bg-white/5"
                  style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}>
                  <RefreshCw size={14} className={captchaLoad ? 'animate-spin' : ''} />
                </button>
              </div>
              <input type="text" placeholder="Ответ на капчу"
                value={captcha} onChange={e => setCaptcha(e.target.value)}
                className="input-search text-sm" autoComplete="off" />
            </div>
          )}

          {isPending && statusLabel && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <Loader2 size={13} className="animate-spin" style={{ color: 'var(--cyan)' }} />
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
              className="flex-1 py-2 rounded-xl text-xs font-semibold disabled:opacity-50 transition-opacity"
              style={{ background: 'var(--cyan)', color: '#000' }}>
              {isPending ? statusLabel : 'Войти'}
            </button>
            <button onClick={() => {
              setShowForm(false); setCaptchaImg(null)
              setConnectStatus('idle'); setErrorMsg(null)
            }}
              disabled={isPending}
              className="px-3 py-2 rounded-xl text-xs hover:bg-white/5 disabled:opacity-50"
              style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}>
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* Connected */}
      {status?.connected && !showForm && (
        <div className="flex flex-col gap-3">
          {status.sync_status === 'ok' && (
            <div className="flex gap-2">
              {[
                { value: status.courses_count, label: 'предметов' },
                { value: status.files_count,   label: 'файлов' },
                { value: status.last_sync
                  ? new Date(status.last_sync).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
                  : '—', label: 'обновлено' },
              ].map((item, i) => (
                <div key={i} className="flex-1 rounded-xl p-2.5 text-center" style={{ background: 'var(--surface)' }}>
                  <div className="text-sm font-bold" style={{ color: 'var(--cyan)' }}>{item.value}</div>
                  <div className="text-[10px]" style={{ color: 'var(--t-muted)' }}>{item.label}</div>
                </div>
              ))}
            </div>
          )}

          {status.error_msg && (
            <p className="text-xs px-3 py-2 rounded-lg"
              style={{ background: '#ef444415', color: '#ef4444', border: '1px solid #ef444425' }}>
              {status.error_msg}
            </p>
          )}

          {syncData?.courses?.length > 0 && (
            <div>
              <button onClick={() => setShowData(!showData)}
                className="flex items-center gap-1 text-xs w-full text-left"
                style={{ color: 'var(--t-secondary)' }}>
                {showData ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {showData ? 'Скрыть предметы' : `Предметы (${syncData.courses.length})`}
              </button>
              {showData && (
                <div className="mt-2 flex flex-col gap-1 max-h-52 overflow-y-auto">
                  {syncData.courses.map((c: any, i: number) => (
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

          <div className="flex gap-2 pt-1 flex-wrap" style={{ borderTop: '1px solid var(--border)' }}>
            <button onClick={() => syncMutation.mutate()} disabled={isRunning || syncMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs disabled:opacity-50 hover:bg-white/5"
              style={{ color: 'var(--cyan)', border: '1px solid var(--cyan)33' }}>
              <RefreshCw size={11} className={isRunning ? 'animate-spin' : ''} />
              Обновить
            </button>
            {/* УЛУЧШЕНИЕ: кнопка экспорта .ics */}
            {status.sync_status === 'ok' && (
              <a
                href="#"
                onClick={async (e) => {
                  e.preventDefault()
                  // Получаем group_id из профиля если есть
                  const { useScheduleStore } = await import('@/lib/store')
                  const store = useScheduleStore.getState()
                  const gid = store.profile?.groupId
                  if (!gid) return
                  const base = process.env.NEXT_PUBLIC_API_URL || ''
                  window.location.href = `${base}/api/schedules/group/${gid}/export.ics?weeks=8`
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs hover:bg-white/5"
                style={{ color: 'var(--t-secondary)', border: '1px solid var(--border)' }}
              >
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
        </div>
      )}
    </div>
  )
}
