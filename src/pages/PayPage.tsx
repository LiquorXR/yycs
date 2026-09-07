import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { Button } from '@/components/ui/button'
import PageHeader from '@/components/PageHeader'
import { getOrder, getOrderReport, type OrderDetail } from '@/api/orders'
import { formatPrice } from '@/lib/format'
import { isSafeCodeUrl, isSafePayUrl, isSafeQrcodeUrl } from '@/lib/url'

interface PayState {
  payType: string | null
  payUrl: string | null
  codeUrl: string | null
}

/** 已支付（付款成功，进入人工交付流程）的订单状态 */
const PAID_STATES = ['PAID', 'UNLOCKED', 'DELIVERED', 'ADDED_WECOM']

function NativeQrArea({ codeUrl }: { codeUrl: string }) {
  return (
    <div className="flex flex-col items-center">
      <div className="relative flex size-[168px] items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-gold/50 bg-white p-2">
        <QRCodeSVG value={codeUrl} size={152} level="M" aria-label="扫码支付" className="size-full" />
      </div>
      <p className="mt-4 text-sm text-fg-secondary">用微信 / 支付宝「扫一扫」完成支付</p>
      <p className="mt-1 text-xs text-muted">扫码失败？请复制下方链接在对应 App 中打开</p>
      <p className="mt-2 w-full max-w-[300px] rounded-lg border border-gold/20 bg-bg/60 px-3 py-2 text-xs text-fg-secondary break-all select-all">
        {codeUrl}
      </p>
    </div>
  )
}

function PayChannelEmpty() {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <span className="grid size-16 place-items-center rounded-full border border-border-gold bg-bg/60 text-muted">
        <svg viewBox="0 0 24 24" className="size-8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="6" width="18" height="13" rx="2.5" />
          <path d="M3 10h18M7 15h4" />
        </svg>
      </span>
      <p className="mt-5 font-kai text-lg font-bold text-gold-light">支付通道即将上线，敬请期待</p>
              <p className="mt-2 text-sm leading-relaxed text-fg-secondary">支付功能正在建设中，完成后即可解锁姻缘完整报告</p>
    </div>
  )
}

export default function PayPage() {
  const { orderNo = '' } = useParams()
  const location = useLocation()
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [payCountdown, setPayCountdown] = useState(899)
  const [wecomUrl, setWecomUrl] = useState<string | null>(null)

  const fetchOrder = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!orderNo) return null
      if (!opts?.silent) setLoading(true)
      try {
        const o = await getOrder(orderNo)
        setOrder(o)
        setError(null)
        return o
      } catch (err) {
        setError(err instanceof Error && err.message ? err.message : '订单信息加载失败，请稍后重试')
        return null
      } finally {
        if (!opts?.silent) setLoading(false)
      }
    },
    [orderNo],
  )

  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setInterval> | undefined
    let pollDelay = 5000
    const schedule = () => {
      timer = setInterval(async () => {
        const o = await fetchOrder({ silent: true })
        if (!active) return
        if (!o || o.state !== 'CREATED') {
          if (timer) clearInterval(timer)
          return
        }
        // 指数退避：5s → 10s → 20s → 30s 封顶，降低服务器读压力
        if (timer) clearInterval(timer)
        pollDelay = Math.min(pollDelay * 2, 30000)
        schedule()
      }, pollDelay)
    }
    void fetchOrder()
    schedule()
    return () => {
      active = false
      if (timer) clearInterval(timer)
    }
  }, [fetchOrder])

  useEffect(() => {
    const t = setInterval(() => setPayCountdown((s) => (s > 0 ? s - 1 : 0)), 1000)
    return () => clearInterval(t)
  }, [])

  // 持久化最近订单，便于付款后重复回看企微码（同设备 last_orderNo + 历史列表，无需跨设备）
  useEffect(() => {
    if (!orderNo) return
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
  }, [orderNo])

  const pay = (location.state as PayState | null) ?? null
  const PAID_AFTER_CLOSE = 'paid_after_close'
  const isPaid = order !== null && PAID_STATES.includes(order.state)

  // 订单翻转为已支付那一刻，只取一次企微加好友链接（用于支付成功卡跳转；wecom=null 时回退查看报告）
  const wecomFetchedRef = useRef(false)
  useEffect(() => {
    if (!orderNo || !order || !PAID_STATES.includes(order.state) || wecomFetchedRef.current) return
    wecomFetchedRef.current = true
    let active = true
    getOrderReport(orderNo)
      .then((r) => {
        if (!active) return
        if (r.wecom?.qrcodeUrl && isSafeQrcodeUrl(r.wecom.qrcodeUrl)) {
          setWecomUrl(r.wecom.qrcodeUrl)
        }
      })
      .catch(() => {
        /* 拉取失败不影响主流程：回退查看报告按钮 */
      })
    return () => {
      active = false
    }
  }, [orderNo, order])
  // 订单加载后以服务端字段为准（防旧 location.state 过期链接）；加载前用首屏透传加速
  const effectivePayType = order?.payType ?? pay?.payType ?? null
  const effectivePayUrl = order?.payUrl ?? pay?.payUrl ?? null
  const effectiveCodeUrl = order?.codeUrl ?? pay?.codeUrl ?? null
  const showH5 = effectivePayType === 'h5' && isSafePayUrl(effectivePayUrl)
  const showNative = effectivePayType === 'native' && isSafeCodeUrl(effectiveCodeUrl)
  // H5 主路径附带聚合码备选（快手 WebView 拦截拉起时用）
  const showH5FallbackQr = showH5 && isSafeCodeUrl(effectiveCodeUrl)
  const showEmpty = !showH5 && !showNative
  const isClosed = order?.state === 'CLOSED'
  const paidAfterClose = !!order?.failReason?.includes(PAID_AFTER_CLOSE)
  const countdownText = `${String(Math.floor(payCountdown / 60)).padStart(2, '0')}:${String(payCountdown % 60).padStart(2, '0')}`

  return (
    <main className="fx-paper fx-cloud min-h-screen pb-28 page-enter">
      <PageHeader title="收银台" backTo={order?.profileId ? `/order?profileId=${order.profileId}` : '/'} />

      <div className="p-4 space-y-3 pb-6">
        {/* 订单支付卡 — 严格原型 */}
        <div className="card-guofeng p-4 text-center">
          {isPaid ? (
            <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-2.5 py-1 text-xs text-emerald-200">
              <span className="size-1.5 shrink-0 rounded-full bg-emerald-400" aria-hidden="true" />
              订单已支付
            </div>
          ) : isClosed ? (
            <div className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-xs text-muted">
              订单已关闭
            </div>
          ) : (
            <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/30 bg-amber-500/15 px-2.5 py-1 text-xs text-amber-200">
              <span className="size-1.5 shrink-0 animate-pulse rounded-full bg-amber-400" aria-hidden="true" />
              订单待支付 · 请尽快完成支付（<span className="font-mono font-bold">{countdownText}</span>）
            </div>
          )}
          <div className="mt-3 text-[13px] text-fg-secondary">
            订单号 <span className="font-mono text-fg">{order?.orderNo ?? orderNo}</span> · 姻缘专属报告
          </div>
          <div className="mt-1 font-kai text-[22px] font-bold leading-none text-gold">
            {order ? formatPrice(order.amount) : '¥9.9'}
          </div>

          {loading ? (
            <div className="mx-auto mt-4 h-44 w-44 animate-pulse rounded-xl bg-gold/10" aria-label="加载中" />
          ) : error ? (
            <div className="py-6">
              <p className="text-sm text-red-light" role="alert">
                {error}
              </p>
              <Button variant="outline" className="mt-4" onClick={() => void fetchOrder()}>
                重新加载
              </Button>
            </div>
          ) : isPaid ? (
            <div className="flex flex-col items-center py-6">
              <span className="grid size-16 place-items-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#591010] shadow-gold">
                <svg viewBox="0 0 24 24" className="size-8" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M5 12l4.5 4.5L19 7" />
                </svg>
              </span>
              <p className="mt-4 font-kai text-lg font-bold text-gold-light">支付成功</p>
              <p className="mt-1 text-sm text-fg-secondary">姻缘天书已解锁，由玄天道长微信人工交付完整报告</p>
              {wecomUrl ? (
                <>
                  <a href={wecomUrl} className="mt-6 w-full max-w-[280px]" rel="noopener noreferrer">
                    <Button size="lg" variant="gold" className="w-full rounded-full text-base font-bold">
                      添加企业微信 · 领取完整报告
                    </Button>
                  </a>
                  <Link to={`/report/${orderNo}`} className="mt-3 block w-full max-w-[280px]">
                    <Button variant="outline" className="w-full rounded-full text-sm">
                      查看完整报告 · 回看企微入口
                    </Button>
                  </Link>
                </>
              ) : (
                <Link to={`/report/${orderNo}`} className="mt-6 w-full max-w-[280px]">
                  <Button size="lg" variant="gold" className="w-full rounded-full text-base font-bold">
                    查看完整报告
                  </Button>
                </Link>
              )}
            </div>
          ) : isClosed ? (
            <div className="flex flex-col items-center py-6 text-center">
              <p className="font-kai text-lg font-bold text-gold-light">订单已关闭</p>
              {paidAfterClose ? (
                <p className="mt-2 max-w-[280px] text-sm leading-relaxed text-fg-secondary">
                  系统检测到关闭后到账，金额原路退回或人工核账中。如已扣款请联系客服（工作时间 9:00-21:00），并提供订单号。
                </p>
              ) : (
                <p className="mt-2 text-sm text-fg-secondary">订单已关闭，如需继续请重新下单。</p>
              )}
              <p className="mt-3 font-mono text-xs text-muted">{order?.orderNo ?? orderNo}</p>
            </div>
          ) : showH5 ? (
            <div className="flex flex-col items-center py-4 text-center">
              <p className="text-sm leading-relaxed text-fg-secondary">
                将拉起支付应用完成支付
                <br />
                支付成功后自动返回本页查看报告
              </p>
              <a href={effectivePayUrl!} rel="noopener noreferrer" className="mt-6 w-full max-w-[280px]">
                <Button size="lg" className="w-full rounded-full text-base font-bold">
                  点击唤起支付
                </Button>
              </a>
              <p className="mt-3 text-xs text-muted">未自动拉起？可点击右上角在浏览器中打开</p>
              {showH5FallbackQr ? (
                <div className="mt-6 w-full border-t border-gold/20 pt-5">
                  <p className="mb-3 text-xs text-muted">拉起被拦截？可用扫码备选支付</p>
                  <NativeQrArea codeUrl={effectiveCodeUrl!} />
                </div>
              ) : null}
            </div>
          ) : showNative ? (
            <div className="mt-4">
              <NativeQrArea codeUrl={effectiveCodeUrl!} />
              <Link to={`/report/${orderNo}`} className="mt-4 block">
                <button type="button" className="h-9 w-full rounded-full bg-jade text-sm font-medium text-white transition hover:bg-[#2f8a6e] [touch-action:manipulation]">
                  我已支付 · 查看报告
                </button>
              </Link>
            </div>
          ) : showEmpty ? (
            <div className="mt-3">
              <PayChannelEmpty />
            </div>
          ) : null}
        </div>

        {!loading && !error && order && !isPaid && order.state === 'CREATED' && !(showH5 || showNative) ? (
          <p className="text-center text-xs text-muted">
            已支付？{' '}
            <button type="button" className="text-gold underline underline-offset-2" onClick={() => void fetchOrder({ silent: true })}>
              刷新支付状态
            </button>
          </p>
        ) : null}

        <div className="card-guofeng flex items-center gap-2.5 p-3.5 text-xs text-fg-secondary">
          <span className="grid size-7 shrink-0 place-items-center rounded-full border border-gold/30 bg-gold/15 text-gold" aria-hidden="true">
            ?
          </span>
          <span className="flex-1">支付遇到问题？可返回重试或联系客服（工作时间 9:00-21:00）</span>
          <button type="button" className="shrink-0 rounded-full border border-gold/30 px-2.5 py-1 text-xs text-gold [touch-action:manipulation]">
            客服
          </button>
        </div>
      </div>
    </main>
  )
}
