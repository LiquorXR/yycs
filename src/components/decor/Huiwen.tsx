import { useId } from 'react'
import { cn } from '@/lib/utils'

interface HuiwenProps {
  className?: string
}

/** 回纹分隔条（线描方形回旋，随 currentColor 着色） */
export function Huiwen({ className }: HuiwenProps) {
  const pid = `huiwen-${useId().replace(/:/g, '')}`
  return (
    <svg
      viewBox="0 0 100 12"
      preserveAspectRatio="none"
      className={cn('block h-3 w-full', className)}
      aria-hidden="true"
    >
      <defs>
        <pattern
          id={pid}
          width="26"
          height="12"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M25 1 H5 a4 4 0 0 0 -4 4 v3 a4 4 0 0 0 4 4 h14 a4 4 0 0 0 4 -4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${pid})`} />
    </svg>
  )
}
