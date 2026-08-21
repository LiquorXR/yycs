import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

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

function Compass() {
  return (
    <div className="relative mx-auto mt-3 flex size-[200px] items-center justify-center">
      <svg
        className="absolute size-[188px] animate-compass"
        viewBox="0 0 200 200"
        aria-hidden="true"
      >
        <circle
          cx="100"
          cy="100"
          r="92"
          fill="none"
          stroke="#e2b45f"
          strokeWidth="1"
          strokeDasharray="4 6"
          opacity={0.9}
        />
        <text x="100" y="18" fill="#e2b45f" fontSize="10" textAnchor="middle" fontFamily="serif">
          子
        </text>
        <text x="182" y="104" fill="#e2b45f" fontSize="10" textAnchor="middle">
          卯
        </text>
        <text x="100" y="186" fill="#e2b45f" fontSize="10" textAnchor="middle">
          午
        </text>
        <text x="18" y="104" fill="#e2b45f" fontSize="10" textAnchor="middle">
          酉
        </text>
      </svg>

      <svg
        className="absolute size-[148px] animate-reverse"
        viewBox="0 0 160 160"
        aria-hidden="true"
      >
        <circle cx="80" cy="80" r="72" fill="none" stroke="#e2b45f" strokeWidth="1.3" />
        <path
          d="M80 6 L80 154 M6 80 L154 80"
          stroke="rgba(226,180,95,0.38)"
          strokeWidth="1"
        />
      </svg>

      <div className="relative grid size-[118px] place-items-center">
        <svg
          className="absolute size-[104px] animate-bagua"
          viewBox="0 0 112 112"
          aria-hidden="true"
        >
          <circle
            cx="56"
            cy="56"
            r="46"
            fill="none"
            stroke="#e2b45f"
            strokeWidth="1"
            strokeDasharray="3 6"
            opacity={0.9}
          />
          {BAGUA.map(({ angle, lines }) => {
            const rad = (angle * Math.PI) / 180
            const x = 56 + 34 * Math.sin(rad)
            const y = 56 - 34 * Math.cos(rad)
            const rows = [4, -3, -10]
            return (
              <g key={angle} transform={`translate(${x} ${y}) rotate(${angle})`}>
                {lines.map((yang, i) =>
                  yang ? (
                    <line
                      key={i}
                      x1="-8"
                      y1={rows[i]}
                      x2="8"
                      y2={rows[i]}
                      stroke="#e2b45f"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  ) : (
                    <g key={i}>
                      <line
                        x1="-8"
                        y1={rows[i]}
                        x2="-1.5"
                        y2={rows[i]}
                        stroke="#e2b45f"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                      <line
                        x1="1.5"
                        y1={rows[i]}
                        x2="8"
                        y2={rows[i]}
                        stroke="#e2b45f"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </g>
                  ),
                )}
              </g>
            )
          })}
        </svg>

        <img
          src="/taiji.svg"
          alt="太极"
          aria-hidden="true"
          className="size-[48px] animate-taiji rounded-full border-2 border-gold bg-white object-contain p-[1px] shadow-[0_0_18px_rgba(226,180,95,0.45)]"
          style={{ filter: 'drop-shadow(0 0 6px rgba(226,180,95,0.35))' }}
        />
      </div>
    </div>
  )
}

/* ---------------- 实时测算喜报播报 ---------------- */

const TICKER_ITEMS = [
  '张** 单人测算 · 预测今年秋季遇到正缘',
  '李** 单人测算 · 正缘桃花期与财运走势 已生成',
  '王** 测算成功 · 婚后财运旺衰与性格解析 已批注',
  '赵** 测算成功 · 获得【大师亲批·避坑锦囊】',
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
    title: '正缘桃花期',
    desc: '精准预测感情关键节点与桃花旺衰年份',
  },
  {
    icon: '财',
    title: '婚后财运旺衰',
    desc: '推演财运走势与置业吸金最佳时机',
  },
  {
    icon: '性',
    title: '性格解析',
    desc: '剖析五行禀性，解锁相处之道与自我认知',
  },
  {
    icon: '避',
    title: '避坑指南',
    desc: '预判运势风险点，提供化解妙招',
  },
]

/* ---------------- 页面 ---------------- */

function LandingPage() {
  return (
    <main className="fx-paper fx-cloud flex min-h-screen flex-col pb-6">
      {/* 顶部高光云纹护栏 — 严格对齐原型 */}
      <section className="relative overflow-hidden bg-[radial-gradient(circle_at_50%_0%,rgba(226,180,95,0.14)_0%,transparent_68%)] px-5 pt-2 pb-3 text-center">
        <span className="relative mb-3 inline-flex items-center gap-1.5 rounded-full border border-gold/35 bg-gold/10 px-3 py-1 text-[11px] tracking-[0.12em] text-gold">
          敕造命盘 · 单人测算 <span className="size-1 rounded-full bg-gold animate-pulse-glow" aria-hidden="true" />
        </span>
        <h1 className="relative mt-3 font-shufa text-[26px] font-bold leading-[1.15] tracking-[0.08em] text-gold-gradient">
          八字命盘 · 运势姻缘
        </h1>
        <p className="relative mt-1.5 text-[12px] tracking-wide text-fg-secondary">
          测算个人五行喜忌 · 预测正缘桃花与运势转折
        </p>

        <Compass />
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-6 left-1/2 h-[48px] w-[260px] -translate-x-1/2 bg-[radial-gradient(ellipse_at_center,rgba(226,180,95,0.16)_0%,transparent_70%)] blur-[6px]"
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
          <button type="button" className="btn-guofeng-primary flex h-[50px] w-full items-center justify-center gap-2 font-kai text-[17px] font-bold tracking-wide">
            <span>立即测算 · 开启个人命盘</span>
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
    </main>
  )
}

export default LandingPage
