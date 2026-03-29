'use client'
import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useScheduleStore } from '@/lib/store'
import { BookOpen, RefreshCw, Trash2, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp, Link, Eye, EyeOff } from 'lucide-react'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '') + '/api/ecampus'

async function authedFetch(path: string, options: RequestInit = {}) {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  console.log('[ecampus] authedFetch token:', token ? token.slice(-20) : 'NULL', path)
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

interface Props { token?: string | null }

export function ECampusSection({ token: _tokenProp }: Props) {
  const { authToken } = useScheduleStore()
  const token = authToken || _tokenProp || null
  const [showForm,  setShowForm]  = useState(false)
  const [showData,  setShowData]  = useState(false)
  const [login,     setLogin]     = useState('')
  const [password,  setPassword]  = useState('')
  const [captcha,   setCaptcha]   = useState('')
  const [showPass,  setShowPass]  = useState(false)
  const [captchaImg, setCaptchaImg] = useState<string | null>(null)
  const [captchaLoading, setCaptchaLoading] = useState(false)
  const qc = useQueryClient()

  const { data: status, isLoading } = useQuery({
    queryKey: ['ecampus-status', token],
    queryFn:  () => authedFetch('/status'),
    enabled:  !!token,
    refetchInterval: (q) => q.state.data?.sync_status === 'running' ? 3000 : 30000,
  })

  const { data: syncData } = useQuery({
    queryKey: ['ecampus-data', token],
    queryFn:  () => authedFetch('/data'),
    enabled:  !!token && status?.sync_status === 'ok',
  })

  const loadCaptcha = useCallback(async () => {
    setCaptchaLoading(true)
    setCaptcha('')
    try {
      const data = await authedFetch('/captcha')
      setCaptchaImg(data.image)
    } catch (e: any) {
      alert('Не удалось загрузить капчу: ' + e.message)
    } finally {
      setCaptchaLoading(false)
    }
  }, [])

  useEffect(() => {
    if (showForm && !captchaImg) loadCaptcha()
  }, [showForm])

  const connectMutation = useMutation({
    mutationFn: () => authedFetch('/connect', {
      method: 'POST',
      body: JSON.stringify({ login, password, captcha_code: captcha }),
    }),
    onSuccess: () => {
      setShowForm(false); setLogin(''); setPassword(''); setCaptcha(''); setCaptchaImg(null)
      qc.invalidateQueries({ queryKey: ['ecampus-status'] })
    },
    onError: (e: any) => {
      // Обновляем капчу при ошибке
      if (e.message.includes('капч') || e.message.includes('captcha')) {
        loadCaptcha()
      }
    }
  })

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

  if (!token) return null

  const isRunning = status?.sync_status === 'running'

  return (
    <div className="card px-5 py-4 mb-4">
      {/* Заголовок */}
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

      {/* Не подключён */}
      {!status?.connected && !showForm && (
        <div className="flex items-center justify-between">
          <p className="text-xs" style={{ color: 'var(--t-muted)' }}>
            Оценки, предметы и материалы из eCampus
          </p>
          <button onClick={() => setShowForm(true)}
            className="shrink-0 ml-3 px-3 py-1.5 rounded-lg text-xs font-semibold"
            style={{ background: 'var(--cyan-dim)', color: 'var(--cyan)', border: '1px solid var(--cyan)33' }}>
            Подключить
          </button>
        </div>
      )}

      {/* Форма подключения */}
      {showForm && (
        <div className="flex flex-col gap-3">
          <p className="text-xs" style={{ color: 'var(--t-muted)' }}>
            Данные хранятся зашифрованными (AES-256). Используйте логин и пароль от eCampus.
          </p>

          <input type="text" placeholder="Логин (email)" value={login}
            onChange={e => setLogin(e.target.value)}
            className="input-search text-sm" autoComplete="username" />

          <div className="relative">
            <input type={showPass ? 'text' : 'password'} placeholder="Пароль"
              value={password} onChange={e => setPassword(e.target.value)}
              className="input-search text-sm w-full pr-16" autoComplete="current-password" />
            <button type="button" onClick={() => setShowPass(!showPass)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs"
              style={{ color: 'var(--t-muted)' }}>
              {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>

          {/* Капча */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              {captchaLoading
                ? <div className="w-32 h-12 rounded-lg animate-pulse" style={{ background: 'var(--border)' }} />
                : captchaImg
                  ? <img src={captchaImg} alt="Капча" className="rounded-lg h-12 object-contain"
                      style={{ background: '#fff', padding: 4 }} />
                  : null
              }
              <button type="button" onClick={loadCaptcha} disabled={captchaLoading}
                className="p-2 rounded-lg transition-colors hover:bg-white/5"
                style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}
                title="Обновить капчу">
                <RefreshCw size={14} className={captchaLoading ? 'animate-spin' : ''} />
              </button>
            </div>
            <input type="text" placeholder="Введите текст с картинки"
              value={captcha} onChange={e => setCaptcha(e.target.value)}
              className="input-search text-sm" autoComplete="off" />
          </div>

          {connectMutation.error && (
            <p className="text-xs px-3 py-2 rounded-lg"
              style={{ background: '#ef444415', color: '#ef4444', border: '1px solid #ef444425' }}>
              {(connectMutation.error as Error).message}
            </p>
          )}

          <div className="flex gap-2">
            <button onClick={() => connectMutation.mutate()}
              disabled={!login || !password || !captcha || connectMutation.isPending}
              className="flex-1 py-2 rounded-xl text-xs font-semibold disabled:opacity-50"
              style={{ background: 'var(--cyan)', color: '#000' }}>
              {connectMutation.isPending ? 'Подключение...' : 'Войти'}
            </button>
            <button onClick={() => { setShowForm(false); setCaptchaImg(null) }}
              className="px-3 py-2 rounded-xl text-xs hover:bg-white/5"
              style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}>
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* Подключён */}
      {status?.connected && !showForm && (
        <div className="flex flex-col gap-3">
          {/* Статистика */}
          {status.sync_status === 'ok' && (
            <div className="flex gap-2">
              {[
                { value: status.courses_count, label: 'предметов' },
                { value: status.files_count,   label: 'файлов' },
                { value: status.last_sync ? new Date(status.last_sync).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) : '—', label: 'обновлено' },
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

          {/* Список предметов */}
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
                    <div key={i} className="flex items-center justify-between px-3 py-2 rounded-lg"
                      style={{ background: 'var(--surface)' }}>
                      <div className="min-w-0">
                        <p className="text-xs truncate" style={{ color: 'var(--t-primary)' }}>
                          {c.name || c.Name || `Предмет ${i + 1}`}
                        </p>
                        {c.term_name && (
                          <p className="text-[10px]" style={{ color: 'var(--t-muted)' }}>{c.term_name}</p>
                        )}
                      </div>
                      {(c.url || c.Url) && (
                        <a href={c.url || c.Url} target="_blank" rel="noopener noreferrer"
                          className="shrink-0 ml-2" style={{ color: 'var(--cyan)' }}>
                          <Link size={11} />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Управление */}
          <div className="flex gap-2 pt-1" style={{ borderTop: '1px solid var(--border)' }}>
            <button onClick={() => syncMutation.mutate()} disabled={isRunning || syncMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs disabled:opacity-50 hover:bg-white/5"
              style={{ color: 'var(--cyan)', border: '1px solid var(--cyan)33' }}>
              <RefreshCw size={11} className={isRunning ? 'animate-spin' : ''} />
              Обновить
            </button>
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
