'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { User, GraduationCap, BookOpen, Search, Check, ChevronRight, Edit2, X } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { useScheduleStore } from '@/lib/store'
import type { UserRole } from '@/lib/store'
import { api } from '@/lib/api'
import { useRouter } from 'next/navigation'

type OnboardStep = 'choose-mode' | 'choose-role' | 'choose-group' | 'choose-teacher' | 'done'

export default function ProfilePage() {
  const router = useRouter()
  const { profile, profileComplete, setProfile, clearProfile } = useScheduleStore()

  const [step, setStep]             = useState<OnboardStep>(profileComplete ? 'done' : 'choose-mode')
  const [selectedRole, setRole]     = useState<UserRole>('student')
  const [query, setQuery]           = useState('')
  const [selectedGroupId, setSGId]  = useState<number | null>(null)
  const [selectedGroupName, setSGN] = useState('')
  const [selectedTeacherId, setSTId]= useState<number | null>(null)
  const [selectedTeacherName, setSTN] = useState('')

  const { data: groupData } = useQuery({
    queryKey: ['search-groups-profile', query],
    queryFn:  () => query.length >= 2 ? api.searchGroups(query) : null,
    enabled:  query.length >= 2 && step === 'choose-group',
  })

  const { data: teacherData } = useQuery({
    queryKey: ['search-teachers-profile', query],
    queryFn:  () => query.length >= 2 ? api.searchTeachers(query) : null,
    enabled:  query.length >= 2 && step === 'choose-teacher',
  })

  function handleSaveProfile() {
    if (selectedRole === 'student' && selectedGroupId) {
      setProfile({ role: 'student', groupId: selectedGroupId, groupName: selectedGroupName, teacherId: null, teacherName: null })
    } else if (selectedRole === 'teacher' && selectedTeacherId) {
      setProfile({ role: 'teacher', groupId: null, groupName: null, teacherId: selectedTeacherId, teacherName: selectedTeacherName })
    }
    setStep('done')
    setTimeout(() => router.push('/schedule'), 300)
  }

  function resetForm() {
    clearProfile()
    setStep('choose-mode')
    setQuery('')
    setSGId(null); setSGN('')
    setSTId(null); setSTN('')
  }

  // DONE STATE
  if (profileComplete && profile && step === 'done') {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Профиль" />
        <div className="animate-fade-up">
          <div className="flex flex-col items-center py-8 gap-4">
            <div className="relative">
              <div className="w-24 h-24 rounded-full flex items-center justify-center"
                style={{ background: 'var(--cyan-dim)', border: '2px solid rgba(92,225,230,0.4)' }}>
                {profile.role === 'student'
                  ? <GraduationCap size={36} style={{ color: 'var(--cyan)' }} />
                  : <BookOpen size={36} style={{ color: 'var(--cyan)' }} />}
              </div>
              <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full flex items-center justify-center"
                style={{ background: 'var(--cyan)' }}>
                <Check size={14} color="#000" />
              </div>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold" style={{ color: 'var(--t-primary)' }}>
                {profile.role === 'student' ? profile.groupName : profile.teacherName}
              </p>
              <p className="text-sm mt-1" style={{ color: 'var(--t-secondary)' }}>
                {profile.role === 'student' ? 'Студент' : 'Преподаватель'}
              </p>
            </div>
          </div>

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

          <div className="flex flex-col gap-3">
            <button
              onClick={() => {
                // Restore profile into store and navigate with explicit URL params
                // so schedule page always shows the user's own entity, not last viewed
                setProfile(profile)
                if (profile.role === 'student' && profile.groupId) {
                  router.push(`/schedule?mode=group&id=${profile.groupId}&name=${encodeURIComponent(profile.groupName || '')}`)
                } else if (profile.role === 'teacher' && profile.teacherId) {
                  router.push(`/schedule?mode=teacher&id=${profile.teacherId}&name=${encodeURIComponent(profile.teacherName || '')}`)
                } else {
                  router.push('/schedule')
                }
              }}
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black transition-opacity hover:opacity-90"
              style={{ background: 'var(--cyan)' }}
            >
              Открыть моё расписание <ChevronRight size={16} />
            </button>
            <button
              onClick={resetForm}
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-medium transition-colors hover:bg-white/5"
              style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}
            >
              <Edit2 size={15} /> Изменить профиль
            </button>
          </div>
        </div>
      </div>
    )
  }

  // CHOOSE MODE
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
            <button
              onClick={() => setStep('choose-role')}
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black transition-opacity hover:opacity-90"
              style={{ background: 'var(--cyan)' }}
            >
              <GraduationCap size={16} /> Настроить профиль
            </button>
            <button
              onClick={() => router.push('/schedule')}
              className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-medium transition-colors hover:bg-white/5"
              style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--t-secondary)' }}
            >
              Без профиля
            </button>
          </div>
        </div>
      </div>
    )
  }

  // CHOOSE ROLE
  if (step === 'choose-role') {
    return (
      <div className="px-4 lg:px-0">
        <PageHeader title="Кто вы?" />
        <div className="animate-fade-up">
          <p className="text-sm mb-6" style={{ color: 'var(--t-secondary)' }}>Выберите вашу роль</p>
          <div className="grid grid-cols-2 gap-3 mb-6">
            {([
              { role: 'student' as UserRole, label: 'Студент', icon: GraduationCap, desc: 'Расписание группы' },
              { role: 'teacher' as UserRole, label: 'Преподаватель', icon: BookOpen, desc: 'Расписание по ФИО' },
            ]).map(({ role, label, icon: Icon, desc }) => (
              <button
                key={role}
                onClick={() => setRole(role)}
                className="card p-4 flex flex-col items-center gap-2 transition-all duration-200"
                style={{
                  border: selectedRole === role ? '2px solid var(--cyan)' : '1px solid var(--border)',
                  background: selectedRole === role ? 'var(--cyan-dim)' : 'var(--card)',
                }}
              >
                <Icon size={28} style={{ color: selectedRole === role ? 'var(--cyan)' : 'var(--t-secondary)' }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--t-primary)' }}>{label}</span>
                <span className="text-[10px]" style={{ color: 'var(--t-muted)' }}>{desc}</span>
              </button>
            ))}
          </div>
          <button
            onClick={() => setStep(selectedRole === 'student' ? 'choose-group' : 'choose-teacher')}
            className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold text-black"
            style={{ background: 'var(--cyan)' }}
          >
            Далее <ChevronRight size={16} />
          </button>
        </div>
      </div>
    )
  }

  // CHOOSE GROUP
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
                  }}
                >
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
            style={{ background: selectedGroupId ? 'var(--cyan)' : 'rgba(92,225,230,0.3)', cursor: selectedGroupId ? 'pointer' : 'not-allowed' }}
          >
            <Check size={16} />
            {selectedGroupId ? `Выбрать ${selectedGroupName}` : 'Выберите группу'}
          </button>
        </div>
      </div>
    )
  }

  // CHOOSE TEACHER
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
                  }}
                >
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
            style={{ background: selectedTeacherId ? 'var(--cyan)' : 'rgba(92,225,230,0.3)', cursor: selectedTeacherId ? 'pointer' : 'not-allowed' }}
          >
            <Check size={16} />
            {selectedTeacherId ? `Выбрать ${selectedTeacherName}` : 'Выберите преподавателя'}
          </button>
        </div>
      </div>
    )
  }

  return null
}
