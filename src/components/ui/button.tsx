import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-all duration-200 outline-none select-none active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-night',
  {
    variants: {
      variant: {
        default:
          'bg-gradient-to-b from-gold-bright via-gold to-gold-dark text-night shadow-gold hover:from-gold hover:to-gold-dark',
        gold: 'border border-gold-bright/60 bg-gradient-to-b from-gold-bright via-gold to-gold-dark text-night shadow-glow hover:from-gold hover:to-gold-dark',
        outline:
          'border border-gold/50 bg-white/5 text-gold-cream hover:border-gold hover:bg-gold/10',
        ghost: 'text-gold-cream hover:bg-white/5',
        link: 'text-gold-cream underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-11 px-5 text-base',
        sm: 'h-9 px-3 text-sm',
        lg: 'h-12 px-6 text-lg',
        xl: 'h-14 px-8 text-lg',
        icon: 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Button, buttonVariants }
