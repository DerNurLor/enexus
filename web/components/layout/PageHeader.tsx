import clsx from 'clsx'

interface PageHeaderProps {
  title: string
  action?: React.ReactNode
  className?: string
}

export function PageHeader({ title, action, className }: PageHeaderProps) {
  return (
    <div className={clsx('flex items-center justify-between px-4 pt-14 pb-4 lg:px-0 lg:pt-0 lg:pb-6', className)}>
      <h1
        className="text-4xl font-bold tracking-tight lg:text-3xl"
        style={{ color: 'var(--t-primary)', letterSpacing: '-0.02em' }}
      >
        {title}
      </h1>
      {action && <div>{action}</div>}
    </div>
  )
}
