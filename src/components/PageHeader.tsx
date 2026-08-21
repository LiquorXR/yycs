import { Link } from 'react-router-dom'

/**
 * 页面顶栏（深色鎏金）：与填写命盘页统一，移除左右装饰线。
 */
function PageHeader({ title, backTo = '/' }: { title: string; backTo?: string }) {
  return (
    <header className="sticky top-0 z-10 border-b border-gold/15 bg-[#3a0a0a]/92 backdrop-blur-md">
      <div className="flex items-center justify-between px-4 h-[48px]">
        <Link
          to={backTo}
          aria-label="返回上一页"
          className="grid size-8 place-items-center rounded-full text-muted transition-colors hover:bg-white/8 hover:text-gold"
        >
          <svg
            viewBox="0 0 24 24"
            className="size-[18px]"
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
        <div className="font-kai text-[15px] font-bold tracking-[0.2em] text-gold-light">
          {title}
        </div>
        <span className="w-8" aria-hidden="true" />
      </div>
    </header>
  )
}

export default PageHeader
