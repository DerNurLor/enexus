import { Map } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'

export default function MapPage() {
  return (
    <div className="px-4 lg:px-0">
      <PageHeader title="Карта" />
      <div
        className="card flex flex-col items-center justify-center py-20 gap-4"
        style={{ minHeight: 400 }}
      >
        <Map size={48} style={{ color: 'var(--t-muted)' }} />
        <span className="text-sm" style={{ color: 'var(--t-muted)' }}>
          Интерактивная карта кампуса
        </span>
        <span className="text-xs" style={{ color: 'var(--t-muted)' }}>
          Скоро
        </span>
      </div>
    </div>
  )
}
