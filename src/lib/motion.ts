/**
 * 动效预设 · 与 src/index.css 令牌保持一致
 * 仅使用 transform / opacity，遵守 60fps 与 prefers-reduced-motion
 */

export const DURATION = {
  fast: 150,
  normal: 250,
  slow: 400,
} as const

export const EASE = {
  outExpo: [0.16, 1, 0.3, 1] as const,
  outCirc: [0.075, 0.82, 0.165, 1] as const,
  springSnappy: { type: 'spring' as const, stiffness: 400, damping: 28 },
  springSmooth: { type: 'spring' as const, stiffness: 300, damping: 30 },
  springBouncy: { type: 'spring' as const, stiffness: 420, damping: 32 },
}

/** 入场：淡入 + 上移 12px */
export const fadeInUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.42, ease: EASE.outExpo },
}

/** 页面转场：右进左出 */
export const pageSlide = {
  initial: { x: 24, opacity: 0 },
  animate: { x: 0, opacity: 1 },
  exit: { x: -12, opacity: 0 },
  transition: { duration: 0.32, ease: EASE.outExpo },
}

/** 错落：容器 + 子项 */
export const staggerContainer = {
  animate: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
}

export const staggerItem = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.38, ease: EASE.outExpo } },
}

/** 按压 */
export const tapScale = {
  whileTap: { scale: 0.97 },
  transition: EASE.springSnappy,
}

/** 悬停微抬（仅 hover 设备生效） */
export const hoverLift = {
  whileHover: { y: -1 },
  transition: { duration: 0.2, ease: EASE.outExpo },
}

/** 进度条 spring */
export const progressSpring = EASE.springSmooth

/** 检测是否应减少动画 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** 生成错落延迟（ms） */
export function staggerDelay(index: number, base = 60): number {
  return index * base
}
