import { Link } from 'react-router-dom'
import { Huiwen } from '@/components/decor/Huiwen'

/**
 * 页面顶栏（国潮红金）：返回 + 标题，样式与测算页保持一致。
 */
function PageHeader({ title, backTo = '/' }: { title: string; backTo?: string }) {
  return (
    <header className="sticky top-0 z-20 border-b border-gold/25 bg-paper/90 backdrop-blur">
      <div className="pt-safe flex items-center justify-between px-5 py-3">
        <Link
          to={backTo}
          aria-label="返回上一页"
          className="flex size-9 items-center justify-center rounded-full text-cinnabar transition-colors hover:bg-cinnabar/8"
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
          <Huiwen className="h-1.5 w-8 text-gold/70" />
          <span className="font-kai text-lg font-bold tracking-[0.25em] text-crimson">
            {title}
          </span>
          <Huiwen className="h-1.5 w-8 text-gold/70" />
        </div>
        <span className="w-9" aria-hidden="true" />
      </div>
    </header>
  )
}

export default PageHeader
