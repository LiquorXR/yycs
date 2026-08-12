import { Link } from 'react-router-dom'
import { Huiwen } from '@/components/decor/Huiwen'

/**
 * 页面顶栏（深色鎏金）：返回 + 标题，样式与各页面保持一致。
 */
function PageHeader({ title, backTo = '/' }: { title: string; backTo?: string }) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-[#0d0604]/90 backdrop-blur-md">
      <div className="pt-safe flex items-center justify-between px-5 py-3">
        <Link
          to={backTo}
          aria-label="返回上一页"
          className="flex size-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-gold/10 hover:text-gold"
        >
          <svg
            viewBox="0 0 24 24"
            className="size-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </Link>
        <div className="flex items-center gap-1.5">
          <Huiwen className="h-1.5 w-8 text-gold/40" />
          <span className="font-kai text-lg font-bold tracking-[0.25em] text-gold-light">
            {title}
          </span>
          <Huiwen className="h-1.5 w-8 text-gold/40" />
        </div>
        <span className="w-9" aria-hidden="true" />
      </div>
    </header>
  )
}

export default PageHeader
