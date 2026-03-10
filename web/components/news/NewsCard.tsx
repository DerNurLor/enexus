import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import clsx from 'clsx'

export type NewsCategory = 'important' | 'academic' | 'events' | 'announcements'

export interface NewsItem {
  id: string
  title: string
  excerpt: string
  category: NewsCategory
  publishedAt: string
  featured?: boolean
  icon?: string
}

const CAT_CONFIG: Record<NewsCategory, { label: string; color: string; bg: string }> = {
  important:     { label: 'ВАЖНО',      color: '#f87171', bg: 'rgba(248,113,113,0.12)' },
  academic:      { label: 'Учёба',      color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  events:        { label: 'События',    color: '#4ade80', bg: 'rgba(74,222,128,0.12)' },
  announcements: { label: 'Объявления', color: '#fb923c', bg: 'rgba(251,146,60,0.12)' },
}

export function NewsCard({ item, featured }: { item: NewsItem; featured?: boolean }) {
  const cfg = CAT_CONFIG[item.category]
  const timeAgo = formatDistanceToNow(new Date(item.publishedAt), { addSuffix: true, locale: ru })

  if (featured) {
    return (
      <div
        className="card p-5 mb-4"
        style={{ background: 'var(--card)', minHeight: 180, position: 'relative', overflow: 'hidden' }}
      >
        {/* Decorative bg */}
        <div
          className="absolute inset-0 flex items-center justify-center opacity-10"
          style={{ fontSize: 80 }}
          aria-hidden
        >
          🎉
        </div>
        <div className="relative">
          <div className="flex items-center gap-2 mb-3">
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded"
              style={{ color: cfg.color, background: cfg.bg }}
            >
              {cfg.label}
            </span>
            <span className="text-xs" style={{ color: 'var(--t-muted)' }}>{timeAgo}</span>
          </div>
          <h2 className="text-lg font-bold leading-tight mb-2" style={{ color: 'var(--t-primary)' }}>
            {item.title}
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--t-secondary)' }}>
            {item.excerpt}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card p-4 flex items-start gap-3">
      {/* Icon */}
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-lg"
        style={{ background: cfg.bg }}
      >
        {item.icon || '📌'}
      </div>
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
            style={{ color: cfg.color, background: cfg.bg }}
          >
            {cfg.label}
          </span>
          <span className="text-xs" style={{ color: 'var(--t-muted)' }}>{timeAgo}</span>
        </div>
        <h3 className="text-sm font-semibold leading-snug mb-1" style={{ color: 'var(--t-primary)' }}>
          {item.title}
        </h3>
        <p className="text-xs leading-relaxed line-clamp-2" style={{ color: 'var(--t-secondary)' }}>
          {item.excerpt}
        </p>
      </div>
    </div>
  )
}
