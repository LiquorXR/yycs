import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getOrder, getOrderReport, type OrderReport } from '@/api/orders'
import { formatPrice } from '@/lib/format'

/** 已解锁（完整报告可用）的订单状态 */
const UNLOCKED_STATES = ['UNLOCKED', 'DELIVERED', 'ADDED_WECOM']

/** 轮询间隔：5s */
const POLL_INTERVAL = 5000

/** 倒计时总秒数：14:59 */
const COUNTDOWN_SECONDS = 899

/** 报告正文样例数据（后端暂不提供可视化数据） */
const SAMPLE = {
  pillars: [
    {
      label: '男主四柱',
      element: '水旺',
      values: ['丙子', '丙申', '壬午', '庚子'],
    },
    {
      label: '女主四柱',
      element: '木旺',
      values: ['戊寅', '癸亥', '乙卯', '己卯'],
    },
  ],
  score: 92,
  rank: '【天作之合 · 上等婚配】',
  scoreNote: '两命阴阳相感，五行互补相生，多为前世相守、今生再续之吉婚',
  radar: {
    axes: ['木', '火', '土', '金', '水'],
    male: [52, 62, 44, 82, 92],
    female: [94, 48, 60, 42, 68],
  },
  analysis: {
    label: '命理总评',
    text: '男命日干属水，生于申月得金水相滋，局中水旺；女命日元为木，生于亥月得水木滋养，局中木旺。男水得女木以泄秀，女木得男水以滋荣，五行气场极为和谐，婚后利于互相带财与事业互扶。',
  },
  karma: [
    {
      title: '前世缘分 · 宿世因果',
      body: '二人前世曾有同舟共济之情，今生相逢于青年之时，初见即有宿昔熟络之感，情丝暗系。',
    },
    {
      title: '相处之道 · 性格互补',
      body: '男方性格沉稳内敛，兼具长远谋划；女方心思细腻，富有同理心。两者相处虽偶有言语微瑕，但大局互助互信。',
    },
  ],
  lockedPreview: [
    {
      title: '未来3年情感磨合与化解危机节点 (2026-2028)',
      body: '推演将在2027年农历八月出现太岁冲克，需注意房屋置业与长辈意见分歧，解化锦囊为...',
    },
    {
      title: '婚后家庭财库与旺夫/旺妻指数预测',
      body: '双方结合后财帛宫逢天乙贵人照临，预计结婚后第2年家宅资产可实现显著提升...',
    },
  ],
}

function isUnlocked(report: OrderReport): boolean {
  return UNLOCKED_STATES.includes(report.state) || report.report.locked === false
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="4" y="11" width="16" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  )
}

/** 国风角花饰角（配合 card-guofeng） */
function Corners() {
  return (
    <>
      <span aria-hidden="true" className="corner corner-tl" />
      <span aria-hidden="true" className="corner corner-tr" />
      <span aria-hidden="true" className="corner corner-bl" />
      <span aria-hidden="true" className="corner corner-br" />
    </>
  )
}

/* ---------------- 五行生克契合雷达图（数据驱动生成） ---------------- */

function WuxingRadar({
  axes,
  male,
  female,
}: {
  axes: string[]
  male: number[]
  female: number[]
}) {
  const cx = 110
  const cy = 96
  const R = 66
  const angle = (i: number) => -Math.PI / 2 + (Math.PI * 2 * i) / axes.length
  const pt = (r: number, i: number) => [
    cx + r * Math.cos(angle(i)),
    cy + r * Math.sin(angle(i)),
  ]
  const toPoints = (data: number[]) =>
    data
      .map((v, i) => pt((R * v) / 100, i).map((n) => n.toFixed(1)).join(','))
      .join(' ')

  return (
    <svg
      width="220"
      height="200"
      viewBox="0 0 220 200"
      role="img"
      aria-label={`五行生克契合雷达图：男主水旺、女主木旺，${axes.join('')}五维对比`}
      className="mx-auto"
    >
      {/* 背景网格环 20/40/60/80/100 */}
      {[20, 40, 60, 80, 100].map((pct) => (
        <polygon
          key={pct}
          points={axes
            .map((_, i) =>
              pt((R * pct) / 100, i).map((n) => n.toFixed(1)).join(','),
            )
            .join(' ')}
          fill="none"
          stroke={pct === 100 ? 'rgba(226,180,95,0.32)' : 'rgba(226,180,95,0.14)'}
          strokeWidth={pct === 100 ? 1.5 : 1}
          strokeDasharray={pct === 100 ? undefined : '3 4'}
        />
      ))}

      {/* 轴射线与刻度标签 */}
      {axes.map((label, i) => {
        const p = pt(R, i)
        const tp = pt(R + 17, i)
        return (
          <g key={label}>
            <line
              x1={cx}
              y1={cy}
              x2={p[0].toFixed(1)}
              y2={p[1].toFixed(1)}
              stroke="rgba(226,180,95,0.16)"
              strokeWidth="1"
            />
            <text
              x={tp[0].toFixed(1)}
              y={(tp[1] + 4).toFixed(1)}
              fill="#e2b45f"
              fontSize="12"
              textAnchor="middle"
              fontWeight="bold"
              style={{ fontFamily: 'var(--font-kai)' }}
            >
              {label}
            </text>
          </g>
        )
      })}

      {/* 数据多边形 */}
      <polygon
        points={toPoints(male)}
        fill="rgba(100,181,246,0.30)"
        stroke="#64b5f6"
        strokeWidth="2"
      />
      <polygon
        points={toPoints(female)}
        fill="rgba(255,128,171,0.30)"
        stroke="#ff80ab"
        strokeWidth="2"
      />

      {/* 顶点数值标注 */}
      {male.map((v, i) => {
        const p = pt((R * v) / 100, i)
        return (
          <text
            key={`m-${i}`}
            x={p[0].toFixed(1)}
            y={(p[1] - 5).toFixed(1)}
            fill="#64b5f6"
            fontSize="9"
            textAnchor="middle"
          >
            {v}
          </text>
        )
      })}
      {female.map((v, i) => {
        const p = pt((R * v) / 100, i)
        return (
          <text
            key={`f-${i}`}
            x={p[0].toFixed(1)}
            y={(p[1] + 12).toFixed(1)}
            fill="#ff80ab"
            fontSize="9"
            textAnchor="middle"
          >
            {v}
          </text>
        )
      })}
    </svg>
  )
}

/* ---------------- 企微活码 + 大师亲批 ---------------- */

function MasterConsult({
  wecom,
  orderNo,
}: {
  wecom: NonNullable<OrderReport['wecom']>
  orderNo: string
}) {
  return (
    <section aria-label="大师一对一亲批">
      <div className="flex items-center gap-3 rounded-[16px] border border-border-gold bg-[#2a1711]/85 p-3.5">
        <span
          aria-hidden="true"
          className="grid size-12 shrink-0 place-items-center rounded-full border-2 border-gold bg-[radial-gradient(circle,#2b110a_0%,#100806_100%)] font-kai text-xl text-gold-light"
        >
          道
        </span>
        <div className="min-w-0 flex-1">
          <h4 className="mb-0.5 font-kai text-[15px] text-gold-light">
            玄天道长 · 1V1 姻缘亲批
          </h4>
          <p className="truncate text-xs text-muted">
            {wecom.note ?? '30年周易合婚经验 · 专属化解符箓与择吉日'}
          </p>
        </div>
        <a href="wecom://" aria-label="添加大师企业微信">
          <span className="seal-mark cursor-pointer">加微信</span>
        </a>
      </div>

      <div className="mt-3 rounded-[16px] border border-border-gold bg-surface-card p-4 text-center">
        <img
          src={wecom.qrcodeUrl}
          alt="企业微信活码二维码"
          className="mx-auto size-44 rounded-lg border border-border-gold bg-white object-contain p-2 shadow-gold"
          loading="lazy"
        />
        <a href="wecom://" className="mt-3 block w-full">
          <button type="button" className="btn-guofeng-gold !text-[15px]">
            添加到企业微信
          </button>
        </a>
        <p className="mt-2 text-xs text-muted">
          未唤起企业微信？请长按上方二维码识别添加
        </p>
      </div>

      <p className="mt-3 text-center text-xs text-muted">报告编号：{orderNo}</p>
    </section>
  )
}

/* ---------------- 页面 ---------------- */

function ReportPage() {
  const { orderNo = '' } = useParams()
  const [report, setReport] = useState<OrderReport | null>(null)
  const [amount, setAmount] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seconds, setSeconds] = useState(COUNTDOWN_SECONDS)
  const inFlightRef = useRef(false)
  const loadedRef = useRef(false)

  /* 订单金额（吸底解锁栏真实价格） */
  useEffect(() => {
    if (!orderNo) return
    let active = true
    getOrder(orderNo)
      .then((o) => {
        if (active) setAmount(o.amount)
      })
      .catch(() => {
        /* 金额取不到时使用兜底价 */
      })
    return () => {
      active = false
    }
  }, [orderNo])

  /* 报告轮询 */
  useEffect(() => {
    if (!orderNo) {
      setLoading(false)
      setError('缺少订单号')
      return
    }
    let active = true
    let timer: ReturnType<typeof setInterval> | undefined

    const load = async () => {
      if (inFlightRef.current) return
      inFlightRef.current = true
      try {
        const r = await getOrderReport(orderNo)
        if (!active) return
        setReport(r)
        setError(null)
        if (isUnlocked(r)) {
          if (timer) clearInterval(timer)
        }
      } catch (err) {
        if (!active) return
        setError(
          err instanceof Error && err.message ? err.message : '获取报告失败，请稍后重试',
        )
        if (timer) clearInterval(timer)
      } finally {
        if (!loadedRef.current) {
          loadedRef.current = true
          setLoading(false)
        }
        inFlightRef.current = false
      }
    }

    void load()
    timer = setInterval(() => {
      void load()
    }, POLL_INTERVAL)

    return () => {
      active = false
      if (timer) clearInterval(timer)
    }
  }, [orderNo])

  /* 限时特惠倒计时（每秒真实递减） */
  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((s) => (s > 0 ? s - 1 : 0))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const unlocked = report ? isUnlocked(report) : false
  const reportTitle = report?.report.title
  const countdown = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(
    seconds % 60,
  ).padStart(2, '0')}.${Math.floor(Math.random() * 9)}`

  return (
    <main className="fx-paper fx-cloud fade-in min-h-screen px-4 pt-4 pb-24">
      {loading ? (
        <div className="animate-pulse space-y-4" aria-label="报告加载中">
          <div className="h-28 rounded-2xl bg-gold/10" />
          <div className="h-80 rounded-2xl bg-gold/8" />
          <div className="h-40 rounded-2xl bg-gold/8" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center px-6 py-14 text-center">
          <span className="grid size-16 place-items-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#2b110a] shadow-[0_0_20px_rgba(226,180,95,0.6)]">
            <LockIcon className="size-8" />
          </span>
          <p className="mt-4 font-kai text-lg font-bold text-gold-light" role="alert">
            {error}
          </p>
          <p className="mt-2 text-sm text-fg-secondary">
            报告可能尚未支付解锁，或订单不存在
          </p>
          <Link to={`/pay/${orderNo}`} className="mt-6 w-full max-w-[280px]">
            <button type="button" className="btn-guofeng-primary">
              前往支付
            </button>
          </Link>
          <Link to="/" className="mt-3 w-full max-w-[280px]">
            <button type="button" className="btn-guofeng-ghost">
              返回首页
            </button>
          </Link>
        </div>
      ) : report ? (
        <div className="space-y-4">
          {/* 顶部黑底金边批书标题 */}
          <section
            className="relative rounded-[16px] border border-border-gold bg-gradient-to-b from-[#2a1711]/90 to-[#1a0d09]/95 p-4 text-center shadow-gold"
            aria-label="报告标题"
          >
            <span className="seal-red absolute top-3 right-3">敕批</span>
            <span className="mb-1.5 inline-block rounded border border-border-gold bg-gold/15 px-2.5 py-0.5 text-[11px] tracking-[0.1em] text-gold">
              周易阴阳五行合婚天书
            </span>
            <h1 className="mb-1 font-kai text-[22px] tracking-[0.05em] text-gold-light">
              {reportTitle ?? '八字合婚 · 姻缘命盘详批'}
            </h1>
            <div className="text-sm text-fg-secondary">
              <span className="text-blue">乾造</span>
              <span className="mx-1">(男方)</span>
              <span className="mx-1.5 text-gold">♥</span>
              <span className="text-pink">坤造</span>
              <span className="mx-1">(女方)</span>
            </div>
          </section>

          {/* 匹配总分英雄卡 */}
          <section
            className="relative rounded-[16px] border border-border-gold bg-[radial-gradient(circle_at_50%_30%,rgba(217,56,41,0.25)_0%,rgba(30,17,13,0.9)_80%)] px-4 py-5 text-center"
            aria-label="匹配总分"
          >
            <div className="relative mx-auto mb-2.5 flex size-[120px] flex-col items-center justify-center">
              <svg
                className="absolute inset-0 size-[120px] -rotate-90"
                viewBox="0 0 120 120"
                aria-hidden="true"
              >
                <circle
                  cx="60"
                  cy="60"
                  r="52"
                  fill="none"
                  stroke="rgba(226,180,95,0.2)"
                  strokeWidth="8"
                />
                <circle
                  cx="60"
                  cy="60"
                  r="52"
                  fill="none"
                  stroke="#e2b45f"
                  strokeWidth="8"
                  strokeDasharray="326"
                  strokeDashoffset="26"
                  strokeLinecap="round"
                />
              </svg>
              <span
                className="font-kai text-[38px] leading-none font-bold text-gold-light"
                style={{ textShadow: '0 0 12px rgba(226,180,95,0.6)' }}
              >
                {SAMPLE.score}
              </span>
              <span className="mt-0.5 text-xs text-muted">契合指数</span>
            </div>

            <div className="mb-1 font-kai text-lg tracking-[0.08em] text-gold">
              {SAMPLE.rank}
            </div>
            <p className="text-xs text-fg-secondary">{SAMPLE.scoreNote}</p>

            {/* 八字四柱排盘对比 */}
            <div className="mt-3 grid grid-cols-2 gap-2.5">
              {SAMPLE.pillars.map((p) => (
                <div
                  key={p.label}
                  className="rounded-[10px] border border-border bg-[#100806]/80 p-2.5 text-xs"
                >
                  <div className="mb-1.5 flex justify-between font-kai font-bold text-gold">
                    <span>{p.label}</span>
                    <span className="text-[10px] font-normal text-muted">
                      {p.element}
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-1 text-center font-kai">
                    {p.values.map((v, i) => (
                      <div
                        key={i}
                        className="rounded border border-gold/15 bg-[#2a1711]/60 px-0.5 py-1"
                      >
                        <div className="mb-0.5 text-[10px] text-muted">
                          {['年', '月', '日', '时'][i]}
                        </div>
                        <div className="text-[13px] font-semibold text-fg">{v}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 五行生克契合雷达图 */}
          <section
            className="rounded-[16px] border border-border-gold bg-surface-card p-4 shadow-card"
            aria-label="五行生克分布雷达图"
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="flex items-center gap-1.5 font-kai text-base text-gold-light">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--color-gold)"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 2a10 10 0 0 1 0 20 10 10 0 0 1 0-20z" />
                  <path d="M12 6v6l4 2" />
                </svg>
                五行生克分布雷达图
              </h3>
              <span className="seal-mark">五行互补</span>
            </div>

            <WuxingRadar
              axes={SAMPLE.radar.axes}
              male={SAMPLE.radar.male}
              female={SAMPLE.radar.female}
            />

            <div className="mt-1.5 flex justify-center gap-5">
              <span className="inline-flex items-center gap-1.5 text-xs text-fg-secondary">
                <i className="size-3 rounded-sm border border-gold/30 bg-blue/55" />
                男主 (水旺)
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs text-fg-secondary">
                <i className="size-3 rounded-sm border border-gold/30 bg-pink/55" />
                女主 (木旺)
              </span>
            </div>

            <p className="mt-2.5 rounded-lg border-l-[3px] border-gold bg-[#100806]/60 p-2.5 text-[13px] leading-relaxed text-fg-secondary">
              <strong>{SAMPLE.analysis.label}：</strong>
              {SAMPLE.analysis.text}
            </p>
          </section>

          {/* 三世因果与姻缘批语 */}
          <section className="card-guofeng" aria-label="三世因果与姻缘批语">
            <Corners />
            <div className="mb-3 flex items-center justify-between">
              <h3 className="flex items-center gap-1.5 font-kai text-base text-gold-light">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--color-gold)"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
                </svg>
                三世因果与姻缘批语
              </h3>
            </div>

            {SAMPLE.karma.map((k) => (
              <div
                key={k.title}
                className="mb-2.5 rounded-[10px] border border-border bg-surface/60 p-3 last:mb-0"
              >
                <h4 className="mb-1 flex items-center gap-1.5 font-kai text-sm text-gold">
                  {k.title}
                </h4>
                <p className="text-[13px] leading-relaxed text-fg-secondary">
                  {k.body}
                </p>
              </div>
            ))}
          </section>

          {/* 深度付费解锁区域 */}
          <section
            className="relative overflow-hidden rounded-[16px] border-[1.5px] border-border-gold bg-gradient-to-b from-[#2a1711]/95 to-[#140a08]/98 p-4 shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
            aria-label="高级婚姻运势深度推演"
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="flex items-center gap-1.5 font-kai text-base text-gold-light">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--color-gold)"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                高级婚姻运势深度推演{unlocked ? '' : ' (未解锁)'}
              </h3>
              {unlocked ? <span className="seal-mark">已解锁</span> : null}
            </div>

            {unlocked ? (
              SAMPLE.lockedPreview.map((k) => (
                <div
                  key={k.title}
                  className="mb-2.5 rounded-[10px] border border-border bg-surface/60 p-3 last:mb-0"
                >
                  <h4 className="mb-1 font-kai text-sm text-gold">{k.title}</h4>
                  <p className="text-[13px] leading-relaxed text-fg-secondary">
                    {k.body}
                  </p>
                </div>
              ))
            ) : (
              <>
                {/* 预览模糊占位 */}
                <div
                  className="pointer-events-none opacity-60"
                  style={{ filter: 'blur(4px)' }}
                >
                  {SAMPLE.lockedPreview.map((k) => (
                    <div
                      key={k.title}
                      className="mb-2.5 rounded-[10px] border border-border bg-surface/60 p-3 last:mb-0"
                    >
                      <h4 className="mb-1 font-kai text-sm text-gold">{k.title}</h4>
                      <p className="text-[13px] leading-relaxed text-fg-secondary">
                        {k.body}
                      </p>
                    </div>
                  ))}
                </div>

                {/* 浮层解锁遮罩 */}
                <div className="absolute inset-x-0 top-[60px] bottom-0 z-10 flex flex-col items-center justify-end bg-gradient-to-b from-[#1e110d]/40 to-[#100806]/98 px-4 py-5 backdrop-blur-[8px]">
                  <span className="mb-2 grid size-11 place-items-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#2b110a] shadow-[0_0_20px_rgba(226,180,95,0.6)]">
                    <LockIcon className="size-6" />
                  </span>
                  <h4 className="mb-1 font-kai text-[17px] text-gold-light">
                    解锁《双人深度婚姻天书报告》
                  </h4>
                  <p className="mb-2.5 text-xs text-fg-secondary">
                    包含未来3年运势转折、婚后财运、避坑锦囊与大师一对一亲批
                  </p>
                  <div className="mb-3 rounded-full border border-accent bg-accent/20 px-2.5 py-0.5 font-mono text-xs text-gold-light">
                    限时特惠名额倒计时{' '}
                    <span role="timer" aria-live="off">
                      {countdown}
                    </span>
                  </div>
                  <Link to={`/pay/${orderNo}`} className="w-full">
                    <button type="button" className="btn-guofeng-ghost">
                      查看完整解锁权益
                    </button>
                  </Link>
                </div>
              </>
            )}
          </section>

          {/* 大师亲批导流（企微数据） */}
          {report.wecom ? (
            <MasterConsult wecom={report.wecom} orderNo={report.orderNo} />
          ) : (
            <p className="text-center text-xs text-muted">报告编号：{report.orderNo}</p>
          )}
        </div>
      ) : null}

      {/* 底部固定解锁栏（真实订单价格） */}
      {report && !unlocked ? (
        <div className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-border-gold bg-bg/95 px-4 pt-2.5 pb-5 backdrop-blur-md">
          <Link to={`/pay/${orderNo}`} className="block">
            <button type="button" className="btn-guofeng-primary">
              <span>
                解锁全套姻缘批书 + 大师亲批 (
                {formatPrice(amount ?? 9900)})
              </span>
            </button>
          </Link>
          <div className="mt-1 flex justify-between px-1 text-[11px] text-muted">
            <span>原价 ¥198 · 已有 28.4 万人解锁</span>
            <span>不支持退款承诺·测算加密</span>
          </div>
        </div>
      ) : null}
    </main>
  )
}

export default ReportPage
