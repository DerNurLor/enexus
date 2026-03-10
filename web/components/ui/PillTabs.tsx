'use client'

import clsx from 'clsx'

interface PillTabsProps<T extends string> {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}

export function PillTabs<T extends string>({ options, value, onChange }: PillTabsProps<T>) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={clsx('pill', value === o.value ? 'pill-active' : 'pill-inactive')}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
