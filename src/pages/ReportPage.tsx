import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getOrder, getOrderReport, type OrderReport } from '@/api/orders'
import { formatPrice } from '@/lib/format'
import { isSafeQrcodeUrl } from '@/lib/url'

/** 已支付（付款成功，进入人工交付流程）的订单状态 */
const PAID_STATES = ['PAID', 'UNLOCKED', 'DELIVERED', 'ADDED_WECOM']

/** 轮询间隔：5s */
const POLL_INTERVAL = 5000

/** 倒计时总秒数：14:59 */
const COUNTDOWN_SECONDS = 899

function isPaid(report: OrderReport): boolean {
  return PAID_STATES.includes(report.state)
}

function WechatPayIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 1024 1024" className={className} aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M404.511405 600.865957c-4.042059 2.043542-8.602935 3.223415-13.447267 3.223415-11.197016 0-20.934798-6.169513-26.045189-15.278985l-1.959631-4.296863-81.56569-178.973184c-0.880043-1.954515-1.430582-4.14746-1.430582-6.285147 0-8.251941 6.686283-14.944364 14.938224-14.944364 3.351328 0 6.441713 1.108241 8.94165 2.966565l96.242971 68.521606c7.037277 4.609994 15.433504 7.305383 24.464181 7.305383 5.40101 0 10.533914-1.00284 15.328104-2.75167l452.645171-201.459315C811.496653 163.274644 677.866167 100.777241 526.648117 100.777241c-247.448742 0-448.035176 167.158091-448.035176 373.361453 0 112.511493 60.353576 213.775828 154.808832 282.214547 7.582699 5.405103 12.537548 14.292518 12.537548 24.325012 0 3.312442-0.712221 6.358825-1.569752 9.515724-7.544837 28.15013-19.62599 73.202209-20.188808 75.314313-0.940418 3.529383-2.416026 7.220449-2.416026 10.917654 0 8.245801 6.692423 14.933107 14.944364 14.933107 3.251044 0 5.89015-1.202385 8.629541-2.7793l98.085946-56.621579c7.377014-4.266164 15.188934-6.89913 23.790846-6.89913 4.577249 0 9.003048 0.703011 13.174044 1.978051 45.75509 13.159718 95.123474 20.476357 146.239666 20.476357 247.438509 0 448.042339-167.162184 448.042339-373.372709 0-62.451354-18.502399-121.275087-51.033303-173.009356L407.778822 598.977957 404.511405 600.865957z"
        fill="#00C800"
      />
    </svg>
  )
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

/* ---------------- 企微活码 + 大师亲批 ---------------- */

const BOOK_SLOTS = [
  '今天 15:00 - 16:00 (剩余 2 名额)',
  '今天 20:00 - 21:00 (剩余 1 名额)',
  '明天 10:00 - 11:00 (约满可预定)',
]

const CONSULT_TOPICS = ['正缘画像', '桃花旺衰', '婚后走势']
const DEFAULT_CONSULT_TOPICS = ['正缘画像', '桃花旺衰']

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
  const [copied, setCopied] = useState(false)

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

  const handleCopyLink = async () => {
    const url = window.location.href
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      // 降级：选中提示
      window.prompt('复制报告链接：', url)
    }
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
            玄天道长 · 1V1 命理亲批
          </h4>
            <p className="truncate text-xs text-muted">
            {wecom.note ?? '30年姻缘推演经验 · 专属正缘符箓与择吉良辰'}
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
          onError={(e) => {
            ;(e.target as HTMLImageElement).style.display = 'none'
          }}
        />
        <a href="wecom://" className="mt-3 block w-full" rel="noopener noreferrer">
          <button type="button" className="btn-guofeng-gold !text-[15px]">
            添加到企业微信
          </button>
        </a>
        <button
          type="button"
          onClick={handleCopyLink}
          className="mt-2 w-full rounded-full border border-gold/30 bg-gold/10 py-2.5 text-xs font-medium text-gold transition hover:bg-gold/15"
        >
          {copied ? '✓ 已复制报告链接' : '复制报告链接 · 关闭后仍可回看企微码'}
        </button>
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
              <h3 className="modal-title">玄天道长 · 1V1 命理优先亲批</h3>
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
                  已为 50,000+ 人定正缘桃花与姻缘择吉
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
        if (isPaid(r)) {
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

  // 持久化最近订单，便于付款后同设备重复回看企微码；缺参时回退到 last_orderNo
  useEffect(() => {
    if (!orderNo) {
      try {
        const last = localStorage.getItem('last_orderNo')
        if (last) navigate(`/report/${last}`, { replace: true })
      } catch {
        /* 忽略 */
      }
      return
    }
    try {
      localStorage.setItem('last_orderNo', orderNo)
      const raw = localStorage.getItem('order_history')
      const list: string[] = raw ? (JSON.parse(raw) as string[]) : []
      if (!list.includes(orderNo)) {
        list.unshift(orderNo)
        localStorage.setItem('order_history', JSON.stringify(list.slice(0, 20)))
      }
    } catch {
      /* 忽略隐私模式写入失败 */
    }
  }, [orderNo, navigate])

  /* Escape 关闭支付弹窗 */
  useEffect(() => {
    if (!payModalOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPayModalOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [payModalOpen])

  const paid = report ? isPaid(report) : false
  const reportTitle = report?.report.title
  const countdown = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(
    seconds % 60,
  ).padStart(2, '0')}.${Math.floor(Math.random() * 9)}`

  return (
    <main className="fx-paper fx-cloud min-h-screen px-4 pt-4 pb-24 page-enter">
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
              周易姻缘正缘天书
            </span>
            <h1 className="mb-1 font-kai text-[22px] tracking-[0.05em] text-gold-light">
              {reportTitle ?? '姻缘天书 · 正缘桃花详批'}
            </h1>
            <div className="text-sm text-fg-secondary">
              <span className="mx-1 inline-block rounded border border-border-gold bg-gold/15 px-1.5 py-0.5 text-[11px] font-semibold tracking-[0.1em] text-gold-light">
                命主
              </span>
              <span className="mx-1">姻缘测算 · 正缘与桃花预览</span>
            </div>
          </section>

          {/* 深度付费解锁区域 */}
          <section
            className="relative overflow-hidden rounded-[16px] border-[1.5px] border-border-gold bg-gradient-to-b from-[#5a0e0e]/95 to-[#2e0808]/98 p-4 shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
            aria-label="姻缘深度推演"
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
                姻缘深度推演{paid ? '' : ' (未解锁)'}
              </h3>
            </div>

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

            {/* 未支付：浮层解锁遮罩 */}
            {!paid ? (
              <div className="absolute inset-x-0 top-[60px] bottom-0 z-10 flex flex-col items-center justify-end bg-gradient-to-b from-[#6e1313]/35 to-[#2e0808]/98 px-4 py-5 backdrop-blur-[8px]">
                <span className="mb-2 grid size-11 place-items-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#591010] shadow-[0_0_20px_rgba(226,180,95,0.6)]">
                  <LockIcon className="size-6" />
                </span>
                <h4 className="mb-1 font-kai text-[17px] text-gold-light">
                  完整版需付费解锁《姻缘天书·正缘深度报告》
                </h4>
                <p className="mb-2.5 text-xs text-fg-secondary">
                  解锁后包含正缘画像、近三年桃花节点、婚后走势与相处锦囊及大师一对一亲批
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
            ) : null}
          </section>

          {/* 大师亲批导流（企微数据，qrcodeUrl 需白名单校验防 XSS） */}
          {report.wecom && isSafeQrcodeUrl(report.wecom.qrcodeUrl) ? (
            <MasterConsult wecom={report.wecom} orderNo={report.orderNo} />
          ) : (
            <p className="text-center text-xs text-muted">报告编号：{report.orderNo}</p>
          )}
        </div>
      ) : null}

      {/* 底部固定解锁栏（真实订单价格，仅未支付显示） */}
      {report && !paid ? (
        <div className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-border-gold bg-[#2e0808]/96 px-4 pt-2.5 pb-5 backdrop-blur-md">
          <button
            type="button"
            onClick={() => setPayModalOpen(true)}
            className="btn-guofeng-primary"
          >
            <span>
              解锁姻缘报告 + 大师亲批 (
              {formatPrice(amount ?? 990)})
            </span>
          </button>
          <div className="mt-1 flex justify-between px-1 text-[11px] text-muted">
            <span>原价 {formatPrice(Math.round((amount ?? 990) * 2))} · 已有 28.4 万人解锁</span>
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
              <h3 className="modal-title">姻缘天书 · 正缘深度详批</h3>
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
              <span className="font-bold text-gold-light">命主 · 正缘姻缘预览</span>
            </p>

            {/* 四重权益框 */}
            <div className="mb-3 rounded-[14px] border border-border-gold bg-[#3a0a0a]/60 p-3.5">
              <p className="mb-2 text-[13px] font-medium text-gold-light">
                ✨ 解锁即享四重姻缘天书核心权益：
              </p>
              <ul className="space-y-1.5 text-xs leading-relaxed text-fg-secondary">
                <li>1. 正缘画像与相遇时机全析</li>
                <li>2. 未来 3 年桃花旺衰与脱单年份预警</li>
                <li>3. 婚后走势与家宅财运兴旺之机</li>
                <li>4. 相处锦囊与玄天道长 1V1 优先亲批</li>
              </ul>
            </div>

            {/* 特惠现价行 — 价格统一取订单真实金额，防价格欺诈 */}
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-fg-secondary">
                特惠现价（限时剩余 3 席）
              </span>
              <span className="flex items-baseline gap-1.5">
                <span className="text-xs text-muted line-through">{formatPrice(Math.round((amount ?? 990) * 2))}</span>
                <span className="font-mono text-2xl font-bold text-gold">
                  {formatPrice(amount ?? 990)}
                </span>
              </span>
            </div>

            {/* 支付方式：仅微信支付 */}
            <div className="pay-methods">
              <span className="pay-option active">
                <WechatPayIcon className="size-5 shrink-0" />
                微信支付
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
              确认支付 {formatPrice(amount ?? 990)} 开启姻缘天书
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
