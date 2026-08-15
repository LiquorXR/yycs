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
    <div className="relative mx-auto mb-4 flex size-[220px] items-center justify-center">
      {/* 外环：描金虚线 + 四正位地支，顺时针慢转 */}
      <svg
        className="absolute size-[210px] animate-compass"
        viewBox="0 0 200 200"
        aria-hidden="true"
      >
        <circle
          cx="100"
          cy="100"
          r="95"
          fill="none"
          stroke="#e2b45f"
          strokeWidth="1"
          strokeDasharray="4 6"
        />
        <text x="100" y="20" fill="#e2b45f" fontSize="10" textAnchor="middle" fontFamily="serif">
          子
        </text>
        <text x="180" y="104" fill="#e2b45f" fontSize="10" textAnchor="middle" fontFamily="serif">
          卯
        </text>
        <text x="100" y="188" fill="#e2b45f" fontSize="10" textAnchor="middle" fontFamily="serif">
          午
        </text>
        <text x="20" y="104" fill="#e2b45f" fontSize="10" textAnchor="middle" fontFamily="serif">
          酉
        </text>
      </svg>

      {/* 内环：鎏金圆环 + 十字轴线，反向缓转 */}
      <svg
        className="absolute size-40 animate-reverse"
        viewBox="0 0 160 160"
        aria-hidden="true"
      >
        <circle
          cx="80"
          cy="80"
          r="75"
          fill="none"
          stroke="#e2b45f"
          strokeWidth="1.5"
        />
        <path
          d="M80 5 L80 155 M5 80 L155 80"
          stroke="rgba(226, 180, 95, 0.4)"
          strokeWidth="1"
        />
      </svg>

      {/* 中心：太极八卦旋转徽章 */}
      <div className="relative grid size-[130px] place-items-center">
        {/* 八卦环：金线刻卦，逆时针缓转 */}
        <svg
          className="absolute size-[112px] animate-bagua"
          viewBox="0 0 112 112"
          aria-hidden="true"
        >
          <circle
            cx="56"
            cy="56"
            r="47"
            fill="none"
            stroke="#e2b45f"
            strokeWidth="1"
            strokeDasharray="3 6"
            opacity="0.9"
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

        {/* 太极：阴阳双鱼，顺时针快转 */}
        <div
          aria-hidden="true"
          className="relative size-[52px] animate-taiji rounded-full border-2 border-gold shadow-[0_0_20px_rgba(226,180,95,0.5)]"
          style={{ background: 'conic-gradient(#f8ebdb 0deg 180deg, #100806 180deg 360deg)' }}
        >
          <span className="absolute top-0 left-1/2 size-1/2 -translate-x-1/2 rounded-full bg-[#f8ebdb] shadow-[inset_0_0_0_4px_#100806]" />
          <span className="absolute bottom-0 left-1/2 size-1/2 -translate-x-1/2 rounded-full bg-[#100806] shadow-[inset_0_0_0_4px_#f8ebdb]" />
        </div>
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
      className="mx-5 mb-4 flex items-center gap-2 overflow-hidden rounded-full border border-border bg-[#3a0a0a]/55 px-3.5 py-1.5 text-xs text-fg-secondary"
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
      />
      <span
        className={`flex-1 truncate whitespace-nowrap transition-opacity duration-200 ${
          fading ? 'opacity-0' : 'opacity-100'
        }`}
      >
        {TICKER_ITEMS[idx]}
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
    <main className="fx-paper fx-cloud fade-in flex min-h-screen flex-col pb-6">
      {/* 顶部高光云纹护栏 */}
      <section className="bg-[radial-gradient(circle_at_50%_0%,rgba(226,180,95,0.16)_0%,transparent_70%)] px-5 pt-5 pb-2.5 text-center">
        <span className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-border-gold bg-gold/12 px-3 py-1 text-[11px] tracking-[0.1em] text-gold">
          敕造命盘 · 单人测算
        </span>
        <h1 className="text-gold-gradient mb-1.5 font-shufa text-[28px] font-bold leading-[1.2] tracking-[0.08em]">
          八字命盘 · 运势姻缘
        </h1>
        <p className="mb-4 text-[13px] tracking-[0.02em] text-fg-secondary">
          测算个人五行喜忌 · 预测正缘桃花与运势转折
        </p>

        <Compass />
      </section>

      <Ticker />

      {/* 4 大核心维度 */}
      <section className="mb-5 grid grid-cols-2 gap-3 px-5">
        {FEATURES.map((f) => (
          <div
            key={f.icon}
            className="flex items-start gap-2.5 rounded-[16px] border border-border-gold bg-[#6e1313]/60 p-3.5"
          >
            <span
              aria-hidden="true"
              className="grid size-8 shrink-0 place-items-center rounded-lg border border-border-gold bg-gold/10 text-base text-gold"
            >
              {f.icon}
            </span>
            <div>
              <h3 className="mb-0.5 font-kai text-sm text-fg">{f.title}</h3>
              <p className="text-[11px] leading-[1.3] text-muted">{f.desc}</p>
            </div>
          </div>
        ))}
      </section>

      {/* 操作区与用户保证 */}
      <section className="flex flex-col gap-3 px-5">
        <Link to="/calc" className="block">
          <button type="button" className="btn-guofeng-primary">
            <span>立即测算 · 开启个人命盘</span>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              aria-hidden="true"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </Link>

        <div className="mt-1 flex justify-center gap-4 text-[11px] text-muted">
          <span className="flex items-center gap-1">
            <svg
              viewBox="0 0 24 24"
              className="size-3 fill-gold"
              aria-hidden="true"
            >
              <path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z" />
            </svg>
            隐私加密传输
          </span>
          <span className="flex items-center gap-1">
            <svg
              viewBox="0 0 24 24"
              className="size-3 fill-gold"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            周易古籍精算
          </span>
          <span className="flex items-center gap-1">
            <svg
              viewBox="0 0 24 24"
              className="size-3 fill-gold"
              aria-hidden="true"
            >
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
            超30万用户验证
          </span>
        </div>
      </section>
    </main>
  )
}

export default LandingPage
