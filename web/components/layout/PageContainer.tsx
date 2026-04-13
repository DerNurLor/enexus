/**
 * web/components/layout/PageContainer.tsx
 *
 * Обёртка с отступами для обычных страниц.
 * Страницы с кастомным layout (карта) НЕ используют этот компонент.
 *
 * Использование:
 *   import { PageContainer } from '@/components/layout/PageContainer'
 *   export default function MyPage() {
 *     return <PageContainer><PageHeader title="..."/>{...}</PageContainer>
 *   }
 */
export function PageContainer({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex-1 max-w-4xl mx-auto w-full px-4 lg:px-8 py-6 lg:py-8">
      {children}
    </div>
  )
}
