import { type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

function useReducedMotion() {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * 路由级转场 — 轻量淡入 + 模糊 + 轻缩放，GPU 合成，无全屏遮罩
 * 修复：移除 View Transition API 的全屏快照覆盖，避免首页被背景遮挡
 */
export default function PageTransition({ children }: { children: ReactNode }) {
  const location = useLocation()
  const reduced = useReducedMotion()

  if (reduced) {
    return (
      <div key={location.pathname} className="fade-in">
        {children}
      </div>
    )
  }

  return (
    <div key={location.pathname} className="page-transition-enter will-change-[transform,opacity,filter] [transform:translateZ(0)]">
      {children}
    </div>
  )
}
