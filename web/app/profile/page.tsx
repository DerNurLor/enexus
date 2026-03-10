'use client'

import { User, Settings, LogIn, LogOut, GraduationCap, BookOpen, Bell } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'

// Mock — replace with real auth state
const MOCK_USER = null // null = guest

export default function ProfilePage() {
  const user = MOCK_USER

  if (!user) {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Профиль" />
        <div className="flex flex-col items-center justify-center py-20 gap-6 animate-fade-up">
          {/* Avatar placeholder */}
          <div
            className="w-24 h-24 rounded-full flex items-center justify-center"
            style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
          >
            <User size={40} style={{ color: 'var(--t-muted)' }} />
          </div>

          <div className="text-center">
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--t-primary)' }}>
              Вы гость
            </h2>
            <p className="text-sm max-w-xs text-center leading-relaxed" style={{ color: 'var(--t-secondary)' }}>
              Войдите чтобы получить доступ к личному расписанию, оценкам и уведомлениям
            </p>
          </div>

          <div className="w-full max-w-xs flex flex-col gap-3">
            <button
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black transition-opacity hover:opacity-90"
              style={{ background: 'var(--cyan)' }}
            >
              <LogIn size={16} />
              Войти
            </button>
            <button
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-medium transition-colors hover:bg-white/5"
              style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}
            >
              <Settings size={16} />
              Настройки
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 lg:px-0">
      <PageHeader title="Профиль" />
      {/* Logged in view — placeholder */}
      <div className="text-center py-10" style={{ color: 'var(--t-muted)' }}>Профиль студента</div>
    </div>
  )
}
