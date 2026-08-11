import { cn } from '@/lib/utils'

/** 双喜「囍」装饰字符（楷体金字） */
export function DoubleHappiness({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn('font-kai text-gold-grad leading-none select-none', className)}
    >
      囍
    </span>
  )
}

/** 星宿点缀（四角星） */
export function StarSeal({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn('shrink-0', className)}
      aria-hidden="true"
    >
      <path
        d="M12 1.5l2.2 6.6 6.9.4-5.4 4.3 1.8 6.7-5.5-4-5.5 4 1.8-6.7-5.4-4.3 6.9-.4z"
        fill="currentColor"
      />
    </svg>
  )
}
