'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '@/components/layout/PageHeader'
import { PillTabs } from '@/components/ui/PillTabs'
import { ExternalLink, RefreshCw, Newspaper } from 'lucide-react'

type FilterValue = 'all' | 'academic' | 'events' | 'announcements'

const FILTER_OPTIONS: { value: FilterValue; label: string }[] = [
  { value: 'all',           label: 'Все' },
  { value: 'academic',      label: 'Учёба' },
  { value: 'events',        label: 'События' },
  { value: 'announcements', label: 'Объявления' },
]

// Простая классификация новостей по ключевым словам в заголовке
function classifyNews(title: string): FilterValue {
  const t = title.toLowerCase()
  if (t.includes('конференц') || t.includes('форум') || t.includes('конкурс') ||
      t.includes('фестиваль') || t.includes('праздник') || t.includes('мероприят'))
    return 'events'
  if (t.includes('расписани') || t.includes('экзамен') || t.includes('сессия') ||
      t.includes('диплом') || t.includes('зачёт') || t.includes('учебн') ||
      t.includes('каникул') || t.includes('поступ'))
    return 'academic'
  return 'announcements'
}

function formatDate(pubDate: string): string {
  try {
    const d = new Date(pubDate)
    if (isNaN(d.getTime())) return pubDate
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
  } catch {
    return pubDate
  }
}

function timeAgo(pubDate: string): string {
  try {
    const d = new Date(pubDate)
    if (isNaN(d.getTime())) return ''
    const diffMs  = Date.now() - d.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    const diffH   = Math.floor(diffMin / 60)
    const diffD   = Math.floor(diffH / 24)
    if (diffMin < 60)  return `${diffMin} мин. назад`
    if (diffH   < 24)  return `${diffH} ч. назад`
    if (diffD   < 7)   return `${diffD} дн. назад`
    return formatDate(pubDate)
  } catch {
    return ''
  }
}

interface NewsItem {
  title:       string
  link:        string
  description: string
  pubDate:     string
  category:    string
}

export default function NewsPage() {
  const [filter, setFilter] = useState<FilterValue>('all')

  const { data, isLoading, isError, refetch, isFetching } = useQuery<{
    items: NewsItem[]
    fetched_at?: string
    error?: string
  }>({
    queryKey: ['ncfu-news'],
    queryFn: async () => {
      const base = process.env.NEXT_PUBLIC_API_URL || ''
      const res = await fetch(`${base}/api/overview/news?limit=30`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    },
    staleTime:      15 * 60 * 1000,  // 15 минут
    gcTime:         30 * 60 * 1000,  // 30 минут в кеше
    retry:          2,
    retryDelay:     3000,
  })

  const items = data?.items ?? []

  const filtered = filter === 'all'
    ? items
    : items.filter(item => classifyNews(item.title) === filter)

  const featured = filtered[0]
  const rest     = filtered.slice(1)

  return (
    <div className="px-4 lg:px-0">
      <PageHeader
        title="Новости"
        action={
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-xl hover:bg-white/5 transition-colors"
            style={{ color: 'var(--t-muted)', border: '1px solid var(--border)' }}
          >
            <RefreshCw size={13} className={isFetching ? 'animate-spin' : ''} />
          </button>
        }
      />

      <div className="mb-4">
        <PillTabs options={FILTER_OPTIONS} value={filter} onChange={setFilter} />
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1,2,3,4].map(i => (
            <div key={i} className="card h-24 animate-pulse" style={{ opacity: 0.5 }} />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center py-16 gap-3">
          <Newspaper size={40} style={{ color: 'var(--t-muted)' }} />
          <span className="text-sm" style={{ color: 'var(--t-muted)' }}>
            Не удалось загрузить новости
          </span>
          <button
            onClick={() => refetch()}
            className="text-xs px-4 py-2 rounded-xl"
            style={{ color: 'var(--cyan)', border: '1px solid rgba(92,225,230,0.3)' }}
          >
            Попробовать снова
          </button>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && filtered.length === 0 && (
        <div className="flex flex-col items-center py-16 gap-3">
          <Newspaper size={40} style={{ color: 'var(--t-muted)' }} />
          <span className="text-sm" style={{ color: 'var(--t-muted)' }}>Новостей нет</span>
        </div>
      )}

      {/* Featured */}
      {!isLoading && featured && (
        <a
          href={featured.link}
          target="_blank"
          rel="noopener noreferrer"
          className="block card mb-4 overflow-hidden hover:border-cyan-400/30 transition-colors"
          style={{ borderLeft: '3px solid var(--cyan)' }}
        >
          <div className="px-4 py-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
                style={{ background: 'rgba(92,225,230,0.1)', color: 'var(--cyan)' }}>
                Главное
              </span>
              <div className="flex items-center gap-1" style={{ color: 'var(--t-muted)' }}>
                <span className="text-[10px]">{timeAgo(featured.pubDate)}</span>
                <ExternalLink size={10} />
              </div>
            </div>
            <p className="text-sm font-semibold leading-snug mb-1.5"
              style={{ color: 'var(--t-primary)' }}>
              {featured.title}
            </p>
            {featured.description && (
              <p className="text-xs leading-relaxed line-clamp-3"
                style={{ color: 'var(--t-secondary)' }}>
                {featured.description}
              </p>
            )}
          </div>
        </a>
      )}

      {/* Rest */}
      {!isLoading && rest.length > 0 && (
        <div className="flex flex-col gap-3 stagger">
          {rest.map((item, i) => (
            <a
              key={`${item.pubDate}-${i}`}
              href={item.link}
              target="_blank"
              rel="noopener noreferrer"
              className="card hover:border-white/20 transition-colors"
            >
              <div className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold leading-snug flex-1"
                    style={{ color: 'var(--t-primary)' }}>
                    {item.title}
                  </p>
                  <ExternalLink size={12} className="shrink-0 mt-0.5"
                    style={{ color: 'var(--t-muted)' }} />
                </div>
                {item.description && (
                  <p className="text-xs mt-1 line-clamp-2 leading-relaxed"
                    style={{ color: 'var(--t-secondary)' }}>
                    {item.description}
                  </p>
                )}
                <p className="text-[10px] mt-1.5" style={{ color: 'var(--t-muted)' }}>
                  {timeAgo(item.pubDate)}
                </p>
              </div>
            </a>
          ))}
        </div>
      )}

      {/* Source attribution */}
      {!isLoading && items.length > 0 && (
        <p className="text-[10px] text-center mt-6 pb-2" style={{ color: 'var(--t-muted)' }}>
          Источник: <a href="https://ncfu.ru" target="_blank" rel="noopener noreferrer"
            style={{ color: 'var(--cyan)' }}>ncfu.ru</a>
        </p>
      )}
    </div>
  )
}
