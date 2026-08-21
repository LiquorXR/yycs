import { useEffect, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * 路由级轻量转场：右进左出 + 淡入，无依赖，仅 transform/opacity
 * 尊重 prefers-reduced-motion，低端机自动降为淡入
 */
export default function PageTransition({ children }: { children: ReactNode }) {
  const location = useLocation()
  const [displayKey, setDisplayKey] = useState(location.pathname)
  const [phase, setPhase] = useState<'enter' | 'exit'>('enter')

  const reduced =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (location.pathname === displayKey) return
    if (reduced) {
      setDisplayKey(location.pathname)
      return
    }
    setPhase('exit')
    const t = window.setTimeout(() => {
      setDisplayKey(location.pathname)
      setPhase('enter')
    }, 120)
    return () => window.clearTimeout(t)
  }, [location.pathname, displayKey, reduced])

  if (reduced) {
    return <div key={displayKey} className="fade-in">{children}</div>
  }

  return (
    <div
      key={displayKey}
      className={
        phase === 'enter'
          ? 'animate-[fade-in-up_0.32s_cubic-bezier(0.16,1,0.3,1)_both] will-change-transform'
          : 'opacity-0 translate-x-[-8px] transition-[transform,opacity] duration-120'
      }
    >
      {children}
    </div>
  )
}
