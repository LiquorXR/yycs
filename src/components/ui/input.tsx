import * as React from 'react'
import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'h-11 w-full rounded-lg border border-gold/40 bg-white px-3.5 text-base text-ink shadow-sm outline-none transition-colors',
        'placeholder:text-ink/35',
        'focus:border-cinnabar focus:ring-2 focus:ring-cinnabar/15',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-[invalid=true]:border-cinnabar',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
