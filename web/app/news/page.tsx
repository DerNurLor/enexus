'use client'

import { useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { PillTabs } from '@/components/ui/PillTabs'
import { NewsCard, NewsItem, NewsCategory } from '@/components/news/NewsCard'

type FilterValue = 'all' | NewsCategory

const FILTER_OPTIONS: { value: FilterValue; label: string }[] = [
  { value: 'all',           label: 'Все' },
  { value: 'academic',      label: 'Учёба' },
  { value: 'events',        label: 'События' },
  { value: 'announcements', label: 'Объявления' },
]

const MOCK_NEWS: NewsItem[] = [
  {
    id: '1',
    title: 'Новый учебный год 2024–2025: открыта регистрация',
    excerpt: 'Регистрация на курсы следующего семестра теперь открыта. Студенты могут получить доступ через студенческий портал.',
    category: 'important',
    publishedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    featured: true,
  },
  {
    id: '2',
    title: 'Опубликовано расписание экзаменов зимней сессии',
    excerpt: 'Расписание экзаменационной сессии утверждено и доступно в системе.',
    category: 'academic',
    publishedAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    icon: '📅',
  },
  {
    id: '3',
    title: 'Библиотека работает до полуночи в период сессии',
    excerpt: 'С 15 декабря главная библиотека будет открыта до полуночи.',
    category: 'announcements',
    publishedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    icon: '📚',
  },
  {
    id: '4',
    title: 'Студенческая конференция «Наука и технологии»',
    excerpt: 'Приглашаем студентов принять участие в ежегодной научной конференции.',
    category: 'events',
    publishedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    icon: '🔬',
  },
]

export default function NewsPage() {
  const [filter, setFilter] = useState<FilterValue>('all')

  const featured = MOCK_NEWS.find((n) => n.featured)
  const rest = MOCK_NEWS.filter((n) => !n.featured && (filter === 'all' || n.category === filter))

  return (
    <div className="px-4 lg:px-0">
      <PageHeader title="Новости" />

      <div className="mb-4">
        <PillTabs options={FILTER_OPTIONS} value={filter} onChange={setFilter} />
      </div>

      {/* Featured */}
      {featured && (filter === 'all' || filter === featured.category) && (
        <NewsCard item={featured} featured />
      )}

      {/* List */}
      <div className="flex flex-col gap-3 stagger">
        {rest.map((item) => (
          <NewsCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  )
}
