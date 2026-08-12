import * as React from 'react'
import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'h-11 w-full rounded-lg border border-gold/20 bg-coal px-3.5 text-base text-ivory shadow-sm outline-none transition-colors [color-scheme:dark]',
        'placeholder:text-mist/45',
        'focus:border-gold focus:ring-2 focus:ring-gold/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-[invalid=true]:border-cinnabar-bright aria-[invalid=true]:focus:ring-cinnabar-bright/20',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
