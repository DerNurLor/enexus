'use client'

import { useEffect, useState } from 'react'

export default function OfflinePage() {
  const [retrying, setRetrying] = useState(false)

  function retry() {
    setRetrying(true)
    setTimeout(() => {
      window.location.href = '/schedule'
    }, 500)
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      gap: '20px',
      background: 'var(--bg, #0a0a0a)',
      color: 'var(--t-secondary, rgba(255,255,255,0.6))',
      fontFamily: 'var(--font-sans, sans-serif)',
      textAlign: 'center',
      padding: '24px',
    }}>
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none"
        stroke="rgba(92,225,230,0.4)" strokeWidth="1.5" strokeLinecap="round">
        <path d="M1 1l22 22"/>
        <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/>
        <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/>
        <path d="M10.71 5.05A16 16 0 0 1 22.56 9"/>
        <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/>
        <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
        <line x1="12" y1="20" x2="12.01" y2="20"/>
      </svg>

      <div>
        <p style={{ fontSize: '18px', fontWeight: 600, color: 'white', marginBottom: 8 }}>
          Нет подключения
        </p>
        <p style={{ fontSize: '14px', maxWidth: 280 }}>
          Расписание которое вы смотрели ранее доступно в кеше — вернитесь назад
        </p>
      </div>

      <button
        onClick={retry}
        disabled={retrying}
        style={{
          padding: '10px 24px',
          borderRadius: '10px',
          background: 'rgba(92,225,230,0.1)',
          border: '1px solid rgba(92,225,230,0.3)',
          color: '#5ce1e6',
          fontSize: '14px',
          fontWeight: 500,
          cursor: retrying ? 'default' : 'pointer',
          opacity: retrying ? 0.6 : 1,
          transition: 'all 0.15s',
        }}
      >
        {retrying ? 'Проверяю...' : 'Попробовать снова'}
      </button>
    </div>
  )
}
