import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getOrder, getOrderReport, type OrderReport } from '@/api/orders'
import { formatPrice } from '@/lib/format'

/** 已解锁（完整报告可用）的订单状态 */
const UNLOCKED_STATES = ['UNLOCKED', 'DELIVERED', 'ADDED_WECOM']

/** 轮询间隔：5s */
const POLL_INTERVAL = 5000

/** 倒计时总秒数：14:59 */
const COUNTDOWN_SECONDS = 899

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

/* ---------------- 企微活码 + 大师亲批 ---------------- */

const BOOK_SLOTS = [
  '今天 15:00 - 16:00 (剩余 2 名额)',
  '今天 20:00 - 21:00 (剩余 1 名额)',
  '明天 10:00 - 11:00 (约满可预定)',
]

const CONSULT_TOPICS = ['正缘结婚最佳年份', '婚后买房置业财运', '双方长辈关系调控']
const DEFAULT_CONSULT_TOPICS = ['正缘结婚最佳年份', '婚后买房置业财运']

function MasterConsult({
  wecom,
  orderNo,
}: {
  wecom: NonNullable<OrderReport['wecom']>
  orderNo: string
}) {
  const [bookingOpen, setBookingOpen] = useState(false)
  const [slot, setSlot] = useState(BOOK_SLOTS[0])
  const [topics, setTopics] = useState<string[]>(DEFAULT_CONSULT_TOPICS)

  /* Escape 关闭预约弹窗 */
  useEffect(() => {
    if (!bookingOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setBookingOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [bookingOpen])

  const toggleTopic = (tag: string) => {
    setTopics((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    )
  }

  const confirmBooking = () => {
    setBookingOpen(false)
    alert(`预约成功！已为您预约「${slot}」时段，玄天道长将尽快与您联系`)
  }

  return (
    <section aria-label="大师一对一亲批">
      <div className="flex items-center gap-3 rounded-[16px] border border-border-gold bg-[#6e1313]/80 p-3.5">
        <span
          aria-hidden="true"
          className="grid size-12 shrink-0 place-items-center rounded-full border-2 border-gold bg-[radial-gradient(circle,#4a0e0e_0%,#2a0808_100%)] font-kai text-xl text-gold-light"
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
        <button
          type="button"
          onClick={() => setBookingOpen(true)}
          aria-label="预约大师亲批"
        >
          <span className="seal-mark cursor-pointer">预约亲批</span>
        </button>
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

      {/* 预约亲批弹窗 */}
      {bookingOpen ? (
        <div
          className="modal-backdrop open"
          role="dialog"
          aria-modal="true"
          aria-label="预约玄天道长亲批"
        >
          <div className="modal-guofeng">
            <div className="modal-header">
              <span
                aria-hidden="true"
                className="grid size-8 shrink-0 place-items-center rounded-full border border-gold bg-red font-kai text-base text-white"
              >
                道
              </span>
              <h3 className="modal-title">玄天道长 · 1V1 姻缘优先亲批</h3>
              <button
                type="button"
                className="modal-close"
                aria-label="关闭"
                onClick={() => setBookingOpen(false)}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  aria-hidden="true"
                >
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 大师介绍卡 */}
            <div className="mb-3 flex items-center gap-3 rounded-[14px] border border-border-gold bg-[#3a0a0a]/60 p-3.5">
              <span
                aria-hidden="true"
                className="grid size-12 shrink-0 place-items-center rounded-full border-2 border-gold bg-red font-kai text-xl text-white shadow-[0_0_12px_rgba(217,56,41,0.4)]"
              >
                道
              </span>
              <div className="min-w-0">
                <h4 className="font-kai text-[15px] text-gold-light">
                  玄天道长 (研几三十载)
                </h4>
                <p className="mt-0.5 text-xs leading-relaxed text-fg-secondary">
                  已为 50,000+ 对新人进行八字合婚与择吉日
                </p>
              </div>
            </div>

            {/* 预约时段 */}
            <label htmlFor="book-slot" className="mb-1 block text-xs text-fg-secondary">
              预约时段
            </label>
            <select
              id="book-slot"
              className="input-guofeng mb-3"
              value={slot}
              onChange={(e) => setSlot(e.target.value)}
            >
              {BOOK_SLOTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>

            {/* 核心咨询问题 */}
            <p className="mb-1.5 text-xs font-medium text-gold-light">
              核心咨询问题 (可多选)
            </p>
            <div className="mb-4 flex flex-wrap gap-2">
              {CONSULT_TOPICS.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTopic(tag)}
                  aria-pressed={topics.includes(tag)}
                  className={`tag-chip ${topics.includes(tag) ? 'active' : ''}`}
                >
                  {tag}
                </button>
              ))}
            </div>

            <button
              type="button"
              className="btn-guofeng-gold"
              onClick={confirmBooking}
            >
              确认预约玄天道长亲批
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}

/* ---------------- 页面 ---------------- */

function ReportPage() {
  const navigate = useNavigate()
  const { orderNo = '' } = useParams()
  const [report, setReport] = useState<OrderReport | null>(null)
  const [amount, setAmount] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seconds, setSeconds] = useState(COUNTDOWN_SECONDS)
  const [payModalOpen, setPayModalOpen] = useState(false)
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

  /* Escape 关闭支付弹窗 */
  useEffect(() => {
    if (!payModalOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPayModalOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [payModalOpen])

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
          <span className="grid size-16 place-items-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#591010] shadow-[0_0_20px_rgba(226,180,95,0.6)]">
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
            className="relative rounded-[16px] border border-border-gold bg-gradient-to-b from-[#5a0e0e]/92 to-[#3a0a0a]/96 p-4 text-center shadow-gold"
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
              <span className="gender-chip gender-chip-male">乾造</span>
              <span className="mx-1">(男方)</span>
              <span className="mx-1.5 text-gold">♥</span>
              <span className="gender-chip gender-chip-female">坤造</span>
              <span className="mx-1">(女方)</span>
            </div>
          </section>

          {/* 已解锁：总分 / 命理总评 / 因果章节 */}
          {unlocked ? (
            <>
              {/* 匹配总分英雄卡 */}
              <section
                className="relative rounded-[16px] border border-border-gold bg-[radial-gradient(circle_at_50%_30%,rgba(226,180,95,0.12)_0%,rgba(110,19,19,0.9)_80%)] px-4 py-5 text-center"
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
                    {report.report.score ?? 0}
                  </span>
                  <span className="mt-0.5 text-xs text-muted">契合指数</span>
                </div>

                <div className="mb-1 font-kai text-lg tracking-[0.08em] text-gold">
                  {report.report.rank ?? ''}
                </div>
                <p className="text-xs text-fg-secondary">
                  {report.report.scoreNote ?? ''}
                </p>
              </section>

              {/* 命理总评 */}
              {report.report.analysis ? (
                <section className="card-guofeng" aria-label="命理总评">
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
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 2a10 10 0 0 1 0 20 10 10 0 0 1 0-20z" />
                        <path d="M12 6v6l4 2" />
                      </svg>
                      {report.report.analysis.label}
                    </h3>
                    <span className="seal-mark">天机批注</span>
                  </div>
                  <p className="rounded-lg border-l-[3px] border-gold bg-[#2e0808]/55 p-2.5 text-[13px] leading-relaxed text-fg-secondary">
                    {report.report.analysis.text}
                  </p>
                </section>
              ) : null}

              {/* 三世因果与姻缘批语 */}
              {report.report.karma && report.report.karma.length ? (
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

                  {report.report.karma.map((k) => (
                    <div
                      key={k.title}
                      className="mb-2.5 rounded-[10px] border border-border bg-[#3a0a0a]/55 p-3 last:mb-0"
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
              ) : null}
            </>
          ) : null}

          {/* 深度付费解锁区域 */}
          <section
            className="relative overflow-hidden rounded-[16px] border-[1.5px] border-border-gold bg-gradient-to-b from-[#5a0e0e]/95 to-[#2e0808]/98 p-4 shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
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
              report.report.lockedPreview.map((k) => (
                <div
                  key={k.title}
                  className="mb-2.5 rounded-[10px] border border-border bg-[#3a0a0a]/55 p-3 last:mb-0"
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
                  {report.report.lockedPreview.map((k) => (
                    <div
                      key={k.title}
                      className="mb-2.5 rounded-[10px] border border-border bg-[#3a0a0a]/55 p-3 last:mb-0"
                    >
                      <h4 className="mb-1 font-kai text-sm text-gold">{k.title}</h4>
                      <p className="text-[13px] leading-relaxed text-fg-secondary">
                        {k.body}
                      </p>
                    </div>
                  ))}
                </div>

                {/* 浮层解锁遮罩 */}
                <div className="absolute inset-x-0 top-[60px] bottom-0 z-10 flex flex-col items-center justify-end bg-gradient-to-b from-[#6e1313]/35 to-[#2e0808]/98 px-4 py-5 backdrop-blur-[8px]">
                  <span className="mb-2 grid size-11 place-items-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#591010] shadow-[0_0_20px_rgba(226,180,95,0.6)]">
                    <LockIcon className="size-6" />
                  </span>
                  <h4 className="mb-1 font-kai text-[17px] text-gold-light">
                    完整版需付费解锁《双人深度婚姻天书报告》
                  </h4>
                  <p className="mb-2.5 text-xs text-fg-secondary">
                    解锁后包含未来3年运势转折、婚后财运、避坑锦囊与大师一对一亲批
                  </p>
                  <div className="mb-3 rounded-full border border-gold bg-gold/16 px-2.5 py-0.5 font-mono text-xs text-gold-light">
                    限时特惠名额倒计时{' '}
                    <span role="timer" aria-live="off">
                      {countdown}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPayModalOpen(true)}
                    className="btn-guofeng-ghost"
                  >
                    查看完整解锁权益
                  </button>
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
        <div className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-border-gold bg-[#2e0808]/96 px-4 pt-2.5 pb-5 backdrop-blur-md">
          <button
            type="button"
            onClick={() => setPayModalOpen(true)}
            className="btn-guofeng-primary"
          >
            <span>
              解锁全套姻缘批书 + 大师亲批 (
              {formatPrice(amount ?? 9900)})
            </span>
          </button>
          <div className="mt-1 flex justify-between px-1 text-[11px] text-muted">
            <span>原价 ¥198 · 已有 28.4 万人解锁</span>
            <span>不支持退款承诺·测算加密</span>
          </div>
        </div>
      ) : null}

      {/* 支付弹窗 */}
      {payModalOpen ? (
        <div
          className="modal-backdrop open"
          role="dialog"
          aria-modal="true"
          aria-label="确认支付解锁天书"
        >
          <div className="modal-guofeng">
            <div className="modal-header">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-gold)"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3.5 7a2.5 2.5 0 0 1 2.5-2.5h14.5V19H6A2.5 2.5 0 0 0 3.5 21.5V7z" />
                <path d="M3.5 7a2.5 2.5 0 0 1 2.5-2.5h14.5V19H6A2.5 2.5 0 0 0 3.5 21.5V7z" opacity="0.45" transform="translate(1 1)" />
                <path d="M3.5 7a2.5 2.5 0 0 1 2.5-2.5h14.5V19H6A2.5 2.5 0 0 0 3.5 21.5V7z" opacity="0.22" transform="translate(2 2)" />
              </svg>
              <h3 className="modal-title">八字合婚天书 · 深度详批</h3>
              <button
                type="button"
                className="modal-close"
                aria-label="关闭"
                onClick={() => setPayModalOpen(false)}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  aria-hidden="true"
                >
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 测算对象 */}
            <p className="mb-3 text-sm text-fg-secondary">
              测算对象：
              <span className="font-bold text-gold-light">李大为 & 林静雅</span>
            </p>

            {/* 四重权益框 */}
            <div className="mb-3 rounded-[14px] border border-border-gold bg-[#3a0a0a]/60 p-3.5">
              <p className="mb-2 text-[13px] font-medium text-gold-light">
                ✨ 解锁即享四重天书核心权益：
              </p>
              <ul className="space-y-1.5 text-xs leading-relaxed text-fg-secondary">
                <li>1. 男女八字五行冲克与大运合化全析</li>
                <li>2. 未来 10 年正缘危机与转折年份预警</li>
                <li>3. 婚后财运旺衰与置业买房最佳时机</li>
                <li>4. 专属化解锦囊与玄天道长 1V1 优先接通</li>
              </ul>
            </div>

            {/* 特惠现价行 */}
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-fg-secondary">
                特惠现价（限时剩余 3 席）
              </span>
              <span className="flex items-baseline gap-1.5">
                <span className="text-xs text-muted line-through">¥198.00</span>
                <span className="font-mono text-2xl font-bold text-gold">
                  ¥28.00
                </span>
              </span>
            </div>

            {/* 支付方式 */}
            <div className="pay-methods">
              <span className="pay-option active">
                <span aria-hidden="true">🟢</span>
                微信支付
              </span>
              <span className="pay-option opacity-60">
                <span aria-hidden="true">🔵</span>
                支付宝
                <span className="text-[10px]">暂未开通</span>
              </span>
            </div>

            <button
              type="button"
              className="btn-guofeng-primary"
              onClick={() => {
                setPayModalOpen(false)
                navigate(`/pay/${orderNo}`)
              }}
            >
              确认支付 ¥28.00 开启天书
            </button>
            <p className="mt-2.5 text-center text-[11px] text-muted">
              🔒 256 位安全加密传输 · 解锁后永久随时查阅
            </p>
          </div>
        </div>
      ) : null}
    </main>
  )
}

export default ReportPage
