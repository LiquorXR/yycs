import * as React from 'react'
import { cn } from '@/lib/utils'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[]
  placeholder?: string
}

/**
 * 移动端友好的原生下拉（子~亥时辰等），避免大体积弹层组件。
 * 样式对齐 shadcn/ui Select 的视觉语言。
 */
function Select({ className, options, placeholder, ...props }: SelectProps) {
  return (
    <div className="relative">
      <select
        className={cn(
          'h-11 w-full cursor-pointer appearance-none rounded-lg border border-ink/20 bg-paper-light/80 px-3.5 text-base text-ink shadow-sm outline-none transition-colors',
          'pr-10',
          'focus:border-cinnabar focus:ring-2 focus:ring-cinnabar/20',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'aria-[invalid=true]:border-cinnabar',
          className,
        )}
        {...props}
      >
        {placeholder ? (
          <option value="" disabled hidden>
            {placeholder}
          </option>
        ) : null}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <svg
        aria-hidden="true"
        viewBox="0 0 16 16"
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-faint"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M4 6l4 4 4-4" />
      </svg>
    </div>
  )
}

export { Select }
