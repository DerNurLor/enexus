import React from 'react'

interface IconProps {
  className?: string
  size?: number
}

const ico = (path: React.ReactNode, size = 24) =>
  ({ className, size: s }: IconProps) => (
    <svg
      width={s ?? size}
      height={s ?? size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {path}
    </svg>
  )

export const IconCalendar = ico(<>
  <rect x="3" y="4" width="18" height="18" rx="2" />
  <path d="M16 2v4M8 2v4M3 10h18" />
  <path d="M8 14h2m2 0h4M8 18h2" />
</>)

export const IconBuilding = ico(<>
  <path d="M3 21h18M5 21V7l7-4 7 4v14" />
  <rect x="9" y="13" width="6" height="8" />
  <path d="M9 10h6" />
</>)

export const IconStar = ico(<>
  <path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 18l-6.2 3.1 1.2-6.9-5-4.9 6.9-1z" />
</>)

export const IconUser = ico(<>
  <circle cx="12" cy="8" r="4" />
  <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
</>)

export const IconSearch = ico(<>
  <circle cx="8.5" cy="8.5" r="5.5" />
  <path d="M14 14l4 4" />
</>)

export const IconX = ico(<>
  <path d="M6 6l12 12M18 6L6 18" />
</>)

export const IconGroup = ico(<>
  <path d="M17 20c0-2.2-2.2-4-5-4s-5 1.8-5 4" />
  <circle cx="12" cy="10" r="3" />
  <path d="M21 20c0-2-1.8-3.6-4-3.8M3 20c0-2 1.8-3.6 4-3.8" />
  <circle cx="19" cy="9" r="2.5" />
  <circle cx="5" cy="9" r="2.5" />
</>)

export const IconTeacher = ico(<>
  <circle cx="12" cy="8" r="4" />
  <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
</>)

export const IconRoom = ico(<>
  <rect x="3" y="3" width="18" height="18" rx="2" />
  <path d="M9 3v18M3 9h6M3 15h6" />
</>)

export const IconChevronUp = ico(<>
  <path d="M18 15l-6-6-6 6" />
</>)

export const IconSend = ico(<>
  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
</>)

export const IconTrash = ico(<>
  <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
</>)
