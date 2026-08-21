import * as React from 'react'
import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'h-11 w-full rounded-[10px] border border-border-gold bg-[#2e0808]/60 px-3.5 text-base text-fg shadow-sm outline-none transition-[border-color,box-shadow] duration-200 will-change-auto',
        'placeholder:text-muted/70',
        'focus:border-gold focus:ring-2 focus:ring-gold/20 focus:shadow-[0_0_0_3px_rgb(226_180_95/0.14),0_0_16px_rgb(226_180_95/0.14)]',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-[invalid=true]:border-red aria-[invalid=true]:focus:ring-red/20',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
