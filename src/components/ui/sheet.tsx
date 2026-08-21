import * as React from 'react'
import { cn } from '@/lib/utils'

interface SheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
  title?: string
}

/**
 * 底部抽屉 Sheet：弹簧动效，遵循 prefers-reduced-motion
 * 纯 CSS 实现，无额外依赖，符合 60fps 约束
 */
export function Sheet({ open, onOpenChange, children, title }: SheetProps) {
  const scrimRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onOpenChange])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[1000] flex items-end justify-center">
      <div
        ref={scrimRef}
        className="absolute inset-0 bg-[#1a0404]/82 backdrop-blur-[6px] animate-[modal-backdrop-in_0.25s_ease_both]"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title ?? '抽屉'}
        className={cn(
          'relative w-full max-w-[420px] max-h-[85vh] overflow-y-auto',
          'bg-[#4a0e0e] border border-border-gold border-b-0 rounded-t-[20px]',
          'px-5 py-5 pb-7',
          'shadow-[0_-8px_32px_rgba(0,0,0,0.7),0_0_20px_rgba(226,180,95,0.35)]',
          'animate-[modal-slide-in_0.32s_cubic-bezier(0.16,1,0.3,1)_both] will-change-transform',
        )}
      >
        {children}
      </div>
    </div>
  )
}
