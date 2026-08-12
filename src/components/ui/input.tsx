import * as React from 'react'
import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'h-11 w-full rounded-[10px] border border-border-gold bg-[#140a08]/80 px-3.5 text-base text-fg shadow-sm outline-none transition-colors',
        'placeholder:text-muted/70',
        'focus:border-gold focus:ring-2 focus:ring-gold/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-[invalid=true]:border-accent aria-[invalid=true]:focus:ring-accent/20',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
