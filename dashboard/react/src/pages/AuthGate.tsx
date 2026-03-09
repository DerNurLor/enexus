import { useState } from 'react'
import { motion } from 'framer-motion'
import { Spinner } from '@/components/common'
import { useAuthStore } from '@/store/auth'
import { loginWithToken, extractError } from '@/api/client'

export function AuthGate() {
  const [token, setToken] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const { setToken: saveToken, setUser } = useAuthStore()

  async function doLogin() {
    const tok = token.trim().replace(/^Bearer /, '')
    if (!tok) { setErr('Введите токен'); return }
    setLoading(true)
    setErr('')
    try {
      const user = await loginWithToken(tok)
      saveToken(tok)
      setUser(user)
    } catch (e) {
      setErr(extractError(e))
    }
    setLoading(false)
  }

  return (
    <div className="auth-wrap">
      <motion.div className="auth-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="auth-title">NCFU Admin</div>
        <div className="auth-sub">ВВЕДИТЕ ТОКЕН ДЛЯ ВХОДА</div>

        <div className="input-group" style={{ marginBottom: 12 }}>
          <div className="input-label">Bearer Token</div>
          <input
            className="input"
            type="password"
            placeholder="eyJ..."
            value={token}
            onChange={(e) => setToken(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doLogin()}
            autoFocus
          />
        </div>

        <button className="btn btn-primary w-full" onClick={doLogin} disabled={loading}>
          {loading ? <><Spinner /> Вход...</> : 'Войти'}
        </button>

        {err && <div className="auth-err">{err}</div>}

        <div style={{ marginTop: 16, fontSize: 9, color: 'var(--t-20)', textAlign: 'center', lineHeight: 1.6 }}>
          Используйте /?secret=... для автологина<br />
          или введите Bearer JWT вручную
        </div>
      </motion.div>
    </div>
  )
}
