import * as React from 'react'
import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'h-11 w-full rounded-lg border border-ink/20 bg-paper-light/80 px-3.5 text-base text-ink shadow-sm outline-none transition-colors',
        'placeholder:text-ink-faint/70',
        'focus:border-cinnabar focus:ring-2 focus:ring-cinnabar/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-[invalid=true]:border-cinnabar aria-[invalid=true]:focus:ring-cinnabar/20',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
