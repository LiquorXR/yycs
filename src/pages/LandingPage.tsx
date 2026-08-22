import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import SiteFooter from '@/components/SiteFooter'

/* ---------------- 罗盘八卦交互动画 ---------------- */

// 八卦三爻（自下而上；true=阳爻实线，false=阴爻断线），先天八卦方位（上北下南）
const BAGUA: { angle: number; lines: [boolean, boolean, boolean] }[] = [
  { angle: 0, lines: [false, false, false] }, // 坤 · 北
  { angle: 45, lines: [true, false, false] }, // 震 · 东北
  { angle: 90, lines: [true, false, true] }, // 离 · 东
  { angle: 135, lines: [true, true, false] }, // 兑 · 东南
  { angle: 180, lines: [true, true, true] }, // 乾 · 南
  { angle: 225, lines: [false, true, true] }, // 巽 · 西南
  { angle: 270, lines: [false, true, false] }, // 坎 · 西
  { angle: 315, lines: [false, false, true] }, // 艮 · 西北
]

/** 12 地支 */
const DIZHI = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'] as const

function Compass() {
  return (
    <div className="relative mx-auto mt-4 flex size-[232px] items-center justify-center [perspective:800px] animate-float-y [animation-duration:5.2s]">
      {/* 环境光晕 */}
      <div aria-hidden="true" className="compass-ring-glow absolute inset-0 animate-pulse-glow-slow" />
      {/* 外层金属立体底盘 */}
      <div aria-hidden="true" className="compass-metal absolute size-[220px] rounded-full" />
      {/* 外层鎏金光泽扫光 */}
      <div
        aria-hidden="true"
        className="absolute size-[220px] rounded-full opacity-[0.18] animate-compass"
        style={{
          background: 'conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(255,255,255,0.55) 22deg, transparent 44deg, transparent 180deg, rgba(226,180,95,0.5) 200deg, transparent 220deg)',
        }}
      />
      {/* 外刻度环 + 12地支 + 24山细刻 */}
      <svg
        className="absolute size-[220px] animate-compass"
        viewBox="0 0 200 200"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="goldStroke" cx="50%" cy="0%" r="140%">
            <stop offset="0%" stopColor="#fef1cf" />
            <stop offset="38%" stopColor="#e2b45f" />
            <stop offset="72%" stopColor="#b88636" />
            <stop offset="100%" stopColor="#7f6429" />
          </radialGradient>
          <filter id="tickGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="1" stdDeviation="1.2" floodColor="#000" floodOpacity="0.55" />
            <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#e2b45f" floodOpacity="0.28" />
          </filter>
        </defs>
        {/* 主虚线外环 */}
        <circle cx="100" cy="100" r="89" fill="none" stroke="url(#goldStroke)" strokeWidth="1.15" strokeDasharray="3.5 7" opacity={0.96} filter="url(#tickGlow)" />
        {/* 内细线 */}
        <circle cx="100" cy="100" r="84.5" fill="none" stroke="rgba(226,180,95,0.32)" strokeWidth="0.7" />
        {/* 24山刻度 */}
        {Array.from({ length: 24 }).map((_, i) => {
          const ang = i * 15
          const rad = (ang * Math.PI) / 180
          const isMain = i % 2 === 0
          const r1 = isMain ? 84.5 : 86
          const r2 = isMain ? 76 : 80
          const x1 = 100 + r1 * Math.sin(rad)
          const y1 = 100 - r1 * Math.cos(rad)
          const x2 = 100 + r2 * Math.sin(rad)
          const y2 = 100 - r2 * Math.cos(rad)
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} className="compass-tick" strokeWidth={isMain ? 1.15 : 0.7} opacity={isMain ? 0.95 : 0.55} />
        })}
        {/* 12地支文字 */}
        {DIZHI.map((z, i) => {
          const ang = i * 30
          const rad = (ang * Math.PI) / 180
          const r = 97
          const x = 100 + r * Math.sin(rad)
          const y = 100 - r * Math.cos(rad)
          return (
            <text key={z} x={x} y={y} textAnchor="middle" dominantBaseline="central" className="compass-label" style={{ transform: `rotate(${ang}deg)`, transformOrigin: `${x}px ${y}px` }}>
              {z}
            </text>
          )
        })}
        {/* 四正方位点缀 */}
        {([0,90,180,270] as const).map((a) => {
          const rad = (a * Math.PI)/180
          const x = 100 + 69 * Math.sin(rad)
          const y = 100 - 69 * Math.cos(rad)
          return <circle key={a} cx={x} cy={y} r={1.35} fill="#e2b45f" opacity={0.95} />
        })}
      </svg>

      {/* 中层十字 + 双环 */}
      <svg
        className="absolute size-[170px] animate-reverse"
        viewBox="0 0 160 160"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="midGold" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fef1cf" stopOpacity="0.95" />
            <stop offset="52%" stopColor="#e2b45f" />
            <stop offset="100%" stopColor="#8c6b2e" />
          </linearGradient>
        </defs>
        <circle cx="80" cy="80" r="71.5" fill="none" stroke="url(#midGold)" strokeWidth="1.05" opacity={0.92} />
        <circle cx="80" cy="80" r="66" fill="none" stroke="rgba(226,180,95,0.18)" strokeWidth="0.6" strokeDasharray="1.5 4" />
        <path d="M80 9 L80 151 M9 80 L151 80" stroke="rgba(226,180,95,0.34)" strokeWidth="0.9" />
        <path d="M80 22 L80 138 M22 80 L138 80" stroke="rgba(226,180,95,0.14)" strokeWidth="0.6" />
        {/* 斜十字 */}
        <path d="M28 28 L132 132 M132 28 L28 132" stroke="rgba(226,180,95,0.11)" strokeWidth="0.55" />
        {/* 四象小点 */}
        {[45,135,225,315].map((a) => {
          const rad=(a*Math.PI)/180
          const x=80+55*Math.sin(rad)
          const y=80-55*Math.cos(rad)
          return <circle key={a} cx={x} cy={y} r={1.1} fill="#fef1cf" opacity={0.9} />
        })}
      </svg>

      {/* 八卦环 */}
      <div className="relative grid size-[130px] place-items-center">
        <svg
          className="absolute size-[120px] animate-bagua"
          viewBox="0 0 112 112"
          aria-hidden="true"
        >
          <defs>
            <filter id="baguaGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="2.2" floodColor="#000" floodOpacity="0.5" />
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#e2b45f" floodOpacity="0.22" />
            </filter>
          </defs>
          <circle cx="56" cy="56" r="48.5" fill="none" stroke="rgba(226,180,95,0.95)" strokeWidth="1.05" strokeDasharray="2.5 5.5" opacity={0.92} filter="url(#baguaGlow)" />
          <circle cx="56" cy="56" r="44" fill="none" stroke="rgba(226,180,95,0.16)" strokeWidth="0.6" />
          {BAGUA.map(({ angle, lines }) => {
            const rad = (angle * Math.PI) / 180
            const x = 56 + 35.5 * Math.sin(rad)
            const y = 56 - 35.5 * Math.cos(rad)
            const rows = [4, -3, -10]
            return (
              <g key={angle} transform={`translate(${x} ${y}) rotate(${angle})`} filter="url(#baguaGlow)">
                {lines.map((yang, i) =>
                  yang ? (
                    <line key={i} x1="-9" y1={rows[i]} x2="9" y2={rows[i]} stroke="#f3d68a" strokeWidth="2.1" strokeLinecap="round" opacity={0.98} />
                  ) : (
                    <g key={i}>
                      <line x1="-9" y1={rows[i]} x2="-1.6" y2={rows[i]} stroke="#f3d68a" strokeWidth="2.1" strokeLinecap="round" />
                      <line x1="1.6" y1={rows[i]} x2="9" y2={rows[i]} stroke="#f3d68a" strokeWidth="2.1" strokeLinecap="round" />
                    </g>
                  ),
                )}
              </g>
            )
          })}
        </svg>

        {/* 内盘立体托 */}
        <div className="absolute size-[72px] rounded-full bg-[radial-gradient(circle_at_32%_28%,#fff7dd_0%,#fef1cf_14%,#e2b45f_38%,#9a7a33_72%,#5a3f14_100%)] p-[1.5px] shadow-[0_2px_0_#7f6429,0_8px_20px_rgba(0,0,0,0.45),0_0_16px_rgba(226,180,95,0.3)]">
          <div className="size-full rounded-full bg-[radial-gradient(circle_at_30%_28%,#ffffff_0%,#fef1cf_18%,#f3d68a_34%,#ffffff_100%)] p-[2px]">
            <img
              src="/taiji.svg"
              alt="太极"
              aria-hidden="true"
              className="size-full animate-taiji rounded-full object-contain shadow-[inset_0_1px_3px_rgba(0,0,0,0.25)]"
              style={{ filter: 'contrast(1.04) saturate(1.06) drop-shadow(0 1px 1px rgba(0,0,0,0.22))' }}
            />
          </div>
          {/* 高光 */}
          <span aria-hidden="true" className="pointer-events-none absolute left-[14%] top-[16%] h-[22%] w-[28%] rounded-[50%] bg-[radial-gradient(ellipse_at_center,rgba(255,255,255,0.88)_0%,transparent_68%)] blur-[0.6px]" />
        </div>

        {/* 绕转粒子 */}
        <span aria-hidden="true" className="absolute size-[64px] animate-compass rounded-full border border-gold/0 [animation-duration:9s]">
          <span className="absolute left-1/2 top-0 size-[3.5px] -translate-x-1/2 -translate-y-[3px] rounded-full bg-gold-light shadow-[0_0_7px_rgba(226,180,95,0.9),0_0_12px_rgba(226,180,95,0.5)]" />
        </span>
        <span aria-hidden="true" className="absolute size-[76px] animate-reverse rounded-full border border-gold/0 [animation-duration:13s]">
          <span className="absolute left-1/2 bottom-0 size-[2.5px] -translate-x-1/2 translate-y-[2px] rounded-full bg-gold/90 shadow-[0_0_6px_rgba(226,180,95,0.75)]" />
        </span>
      </div>
    </div>
  )
}

/* ---------------- 实时测算喜报播报 ---------------- */

const TICKER_ITEMS = [
  '张** 姻缘测算 · 正缘桃花期已定 · 今年秋季易遇良缘',
  '李** 姻缘测算 · 正缘画像与桃花旺衰 已生成',
  '王** 姻缘测算 · 婚后走势与相处之道 已批注',
  '赵** 姻缘测算 · 获得【大师亲批·正缘锦囊】',
]

const TICKER_INTERVAL = 3500

function Ticker() {
  const [idx, setIdx] = useState(0)
  const [fading, setFading] = useState(false)
  const pausedRef = useRef(false)

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) return
    const timer = setInterval(() => {
      if (pausedRef.current) return
      setFading(true)
      window.setTimeout(() => {
        setIdx((i) => (i + 1) % TICKER_ITEMS.length)
        setFading(false)
      }, 200)
    }, TICKER_INTERVAL)
    return () => clearInterval(timer)
  }, [])

  return (
    <div
      className="mx-5 mb-3 flex items-center gap-2 overflow-hidden rounded-full border border-gold/20 bg-[#3a0a0a]/58 px-3 py-1.5 text-xs text-fg-secondary backdrop-blur"
      role="status"
      aria-live="polite"
      tabIndex={0}
      onMouseEnter={() => {
        pausedRef.current = true
      }}
      onMouseLeave={() => {
        pausedRef.current = false
      }}
      onFocus={() => {
        pausedRef.current = true
      }}
      onBlur={() => {
        pausedRef.current = false
      }}
    >
      <span
        aria-hidden="true"
        className="size-1.5 shrink-0 animate-pulse-glow rounded-full bg-red shadow-[0_0_8px_var(--color-red)]"
        style={{ background: '#d93829', boxShadow: '0 0 8px #d93829' }}
      />
      <span
        className={`flex-1 truncate whitespace-nowrap transition-opacity duration-200 ${
          fading ? 'opacity-0' : 'opacity-100'
        }`}
      >
        {TICKER_ITEMS[idx]}
      </span>
      <span className="shrink-0 rounded-full border border-gold/20 bg-gold/10 px-1.5 py-0.5 text-[10px] leading-none text-gold">
        实时
      </span>
    </div>
  )
}

/* ---------------- 核心维度 ---------------- */

const FEATURES = [
  {
    icon: '缘',
    title: '正缘画像',
    desc: '八字定正缘，推演相遇时机与良人画像',
  },
  {
    icon: '桃',
    title: '桃花旺衰',
    desc: '推演近三年桃花走势与脱单关键年份',
  },
  {
    icon: '婚',
    title: '婚后走势',
    desc: '姻缘视角看婚后财运与家宅兴旺之势',
  },
  {
    icon: '合',
    title: '相处锦囊',
    desc: '以正缘为本，解相处之道与避坑良方',
  },
]

/* ---------------- 页面 ---------------- */

function LandingPage() {
  return (
    <main className="fx-paper fx-cloud flex min-h-screen flex-col pb-6">
      {/* 顶部滚动免责提示栏 */}
      <div className="sticky top-0 z-30 overflow-hidden border-b border-gold/12 bg-[#1a0505]/92 backdrop-blur-md supports-[backdrop-filter]:bg-[#1a0505]/80">
        <div className="flex select-none items-center gap-1 py-[6px] text-[10px] leading-none tracking-wide text-gold/90">
          <span className="ml-2 inline-flex shrink-0 items-center gap-1 rounded-full bg-gold/12 px-1.5 py-0.5 text-[9px] font-bold tracking-[0.08em] text-gold-light">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 2l7 4v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6l7-4z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
            声明
          </span>
          <div className="relative flex flex-1 overflow-hidden">
            <div className="flex animate-[marquee_18s_linear_infinite] whitespace-nowrap will-change-transform hover:[animation-play-state:paused] motion-reduce:animate-none">
              <span className="mx-4">本页面内容仅供娱乐参考，不适用于18周岁以下未成年人。您的数据安全由阿里云提供全面技术保障，我们严格遵循相关法律法规及用户协议，对您的个人信息实施全方位防护，请您放心使用。</span>
              <span className="mx-4" aria-hidden="true">本页面内容仅供娱乐参考，不适用于18周岁以下未成年人。您的数据安全由阿里云提供全面技术保障，我们严格遵循相关法律法规及用户协议，对您的个人信息实施全方位防护，请您放心使用。</span>
            </div>
          </div>
        </div>
      </div>
      {/* 顶部高光云纹护栏 — 严格对齐原型 */}
      <section className="relative overflow-hidden bg-[radial-gradient(circle_at_50%_0%,rgba(226,180,95,0.16)_0%,transparent_68%)] px-5 pt-3 pb-4 text-center">
        <span className="relative mb-3 inline-flex items-center gap-1.5 rounded-full border border-gold/35 bg-gold/10 px-3 py-1 text-[11px] tracking-[0.12em] text-gold shadow-[0_2px_10px_rgba(226,180,95,0.18)]">
          姻缘天定 · 正缘测算 <span className="size-1 rounded-full bg-gold animate-pulse-glow" aria-hidden="true" />
        </span>
        <h1 className="title-gold-3d relative mt-3 font-shufa text-[32px] font-bold leading-[1.08] tracking-[0.08em]">
          正缘姻缘 · 桃花定盘
        </h1>
        <p className="relative mt-1.5 text-[12px] tracking-[0.06em] text-fg-secondary drop-shadow-[0_1px_4px_rgba(0,0,0,0.45)]">
          八字定正缘画像 · 推演桃花旺衰与脱单良机
        </p>

        <Compass />
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-6 left-1/2 h-[52px] w-[272px] -translate-x-1/2 bg-[radial-gradient(ellipse_at_center,rgba(226,180,95,0.14)_0%,transparent_70%)] blur-[6px]"
        />
      </section>

      <Ticker />

      {/* 4 大核心维度 — 超紧凑（二次压缩） */}
      <section className="mb-5 grid grid-cols-2 gap-2.5 px-5">
        {FEATURES.map((f, i) => (
          <div
            key={f.icon}
            className="group relative overflow-hidden rounded-[11px] border border-[#a8833f]/40 bg-[linear-gradient(180deg,rgba(140,26,26,0.94)_0%,rgba(74,14,14,0.98)_100%)] px-3 py-2 shadow-[0_3px_12px_rgba(0,0,0,0.24),inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-[6px] transition-all duration-300 hover:-translate-y-[1px] hover:border-gold/60 active:scale-[0.98]"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gold/35 to-transparent"
            />
            <div className="flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className="grid size-[22px] shrink-0 place-items-center rounded-[6px] border border-gold/30 bg-[linear-gradient(135deg,#fef1cf_0%,#e2b45f_55%,#b88636_100%)] font-kai text-[12px] font-bold leading-none text-[#591010] shadow-[0_1px_5px_rgba(226,180,95,0.3),inset_0_1px_0_rgba(255,255,255,0.65)] transition-transform duration-300 group-hover:scale-[1.04]"
              >
                {f.icon}
              </span>
              <h3 className="font-kai text-[12px] font-bold tracking-[0.02em] text-gold-light leading-none">
                {f.title}
              </h3>
            </div>
            <div className="mt-1.5 h-px w-full bg-gradient-to-r from-gold/12 via-gold/5 to-transparent" />
            <p className="mt-1 text-[10.5px] leading-[1.38] text-[#e8d9b6]/75 line-clamp-2">
              {f.desc}
            </p>
          </div>
        ))}
      </section>

      {/* 操作区与用户保证 — 严格对齐原型 */}
      <section className="mt-4 flex flex-col gap-3 px-5 pb-6">
        <Link to="/calc" className="block">
          <button
            type="button"
            className="btn-guofeng-primary flex h-[50px] w-full items-center justify-center gap-2 font-kai text-[17px] !font-bold tracking-wide [font-synthesis:weight]"
            style={{ fontSynthesis: 'weight', WebkitTextStroke: '0.2px currentColor', paintOrder: 'stroke fill' } as React.CSSProperties}
          >
            <span className="font-bold [font-synthesis:weight]" style={{ fontSynthesis: 'weight', WebkitTextStroke: '0.22px currentColor', paintOrder: 'stroke fill' } as React.CSSProperties}>
              立即测姻缘 · 定正缘桃花期
            </span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </Link>

        <div className="mt-1 flex justify-center gap-4 text-[11px] text-muted">
          <span className="flex items-center gap-1">
            <svg viewBox="0 0 24 24" className="size-3 fill-gold" aria-hidden="true">
              <path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z" />
            </svg>
            隐私加密传输
          </span>
          <span className="flex items-center gap-1">
            <svg viewBox="0 0 24 24" className="size-3 fill-gold" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" stroke="#3a0a0a" strokeWidth="1.5" fill="none" />
            </svg>
            周易古籍精算
          </span>
          <span className="flex items-center gap-1">
            <svg viewBox="0 0 24 24" className="size-3 fill-gold" aria-hidden="true">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
            超30万用户验证
          </span>
        </div>
        <div className="flex items-center justify-center gap-2 text-[10px] tracking-[0.12em] text-white/35">
          <span className="h-px w-8 bg-white/10" aria-hidden="true" />
          国风玄学 · 鎏金美学
          <span className="h-px w-8 bg-white/10" aria-hidden="true" />
        </div>
      </section>
      <SiteFooter />
    </main>
  )
}

export default LandingPage
