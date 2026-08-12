import { cn } from '@/lib/utils'

const CLOUD =
  'M20 80 A 20 20 0 0 1 20 40 A 25 25 0 0 1 65 15 A 25 25 0 0 1 115 15 A 25 25 0 0 1 160 40 A 20 20 0 0 1 160 80 Z'

interface XiangyunProps {
  className?: string
  /** true: 剪影填充；false: 线描 */
  filled?: boolean
}

/** 祥云装饰（线描或剪影，随 currentColor 着色） */
export function Xiangyun({ className, filled = false }: XiangyunProps) {
  return (
    <svg
      viewBox="0 0 180 110"
      className={cn('shrink-0', className)}
      aria-hidden="true"
    >
      <path
        d={CLOUD}
        fill={filled ? 'currentColor' : 'none'}
        stroke={filled ? 'none' : 'currentColor'}
        strokeWidth="3.5"
        strokeLinejoin="round"
      />
      {!filled ? (
        <path
          d="M90 84 c0 -14 12 -22 22 -18 m -22 18 a14 14 0 0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      ) : (
        <path
          d="M90 84 c0 -14 12 -22 22 -18"
          fill="none"
          stroke="currentColor"
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      )}
    </svg>
  )
}
