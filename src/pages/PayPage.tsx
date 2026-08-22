import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import PageHeader from '@/components/PageHeader'
import { getOrder, type OrderDetail } from '@/api/orders'
import { formatPrice } from '@/lib/format'
import { isSafeCodeUrl, isSafePayUrl } from '@/lib/url'

interface PayState {
  payType: string | null
  payUrl: string | null
  codeUrl: string | null
}

function NativeQrArea({ codeUrl }: { codeUrl: string }) {
  return (
    <div className="flex flex-col items-center">
      <div className="relative flex size-[168px] items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-gold/50 bg-white p-2">
        <span aria-hidden="true" className="absolute inset-0 bg-gradient-to-r from-transparent via-black/[0.06] to-transparent -translate-x-full animate-[shimmer_2s_linear_infinite]" />
        <svg viewBox="0 0 100 100" className="size-full" aria-hidden="true">
          <rect x="6" y="6" width="34" height="34" fill="none" stroke="#e2b45f" strokeWidth="5" />
          <rect x="60" y="6" width="34" height="34" fill="none" stroke="#e2b45f" strokeWidth="5" />
          <rect x="6" y="60" width="34" height="34" fill="none" stroke="#e2b45f" strokeWidth="5" />
          <path d="M16 16h14v14H16z M70 16h14v14H70z M16 70h14v14H16z" fill="#e2b45f" />
          <path d="M10 46h10v5H10z M10 60h5v5H10z M20 50h5v10h-5z M34 44h8v4h-8z M38 54h6v6h-6z M52 12h6v4h-6z M58 20h8v8h-8z M52 30h5v6h-5z M64 10h4v6h-4z M46 52h6v4h-6z M56 56h4v4h-4z M52 70h10v6h-10z M70 54h8v6h-8z M66 44h4v6h-4z M80 40h6v8h-6z M80 54h6v5h-6z M46 70h4v6h-4z" fill="#e2b45f" />
        </svg>
        <span className="absolute right-1.5 bottom-1.5 rounded bg-surface px-1 py-0.5 text-[10px] leading-none text-muted">长按保存</span>
      </div>
      <p className="mt-4 text-sm text-fg-secondary">长按二维码保存到相册，打开微信「扫一扫」完成支付</p>
      <p className="mt-1 text-xs text-muted">长按识别失败？请复制下方链接在微信中打开</p>
      <p className="mt-2 w-full max-w-[300px] rounded-lg border border-gold/20 bg-[#2e0808]/60 px-3 py-2 text-xs text-fg-secondary break-all select-all">
        {codeUrl}
      </p>
    </div>
  )
}

function PayChannelEmpty() {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <span className="grid size-16 place-items-center rounded-full border border-border-gold bg-[#2e0808]/60 text-muted">
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
    void fetchOrder()
    timer = setInterval(async () => {
      const o = await fetchOrder({ silent: true })
      if (!active) return
      if (!o || o.state !== 'CREATED') {
        if (timer) clearInterval(timer)
      }
    }, 3000)
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
  const isPaid = order?.state === 'PAID'
  // 有效支付信息优先取 location.state，刷新后回退到 order 字段（均需白名单校验）
  const effectivePayType = pay?.payType ?? order?.payType ?? null
  const effectivePayUrl = pay?.payUrl ?? order?.payUrl ?? null
  const effectiveCodeUrl = pay?.codeUrl ?? order?.codeUrl ?? null
  const showH5 = effectivePayType === 'h5' && isSafePayUrl(effectivePayUrl)
  const showNative = effectivePayType === 'native' && isSafeCodeUrl(effectiveCodeUrl)
  const showEmpty = !showH5 && !showNative
  const countdownText = `${String(Math.floor(payCountdown / 60)).padStart(2, '0')}:${String(payCountdown % 60).padStart(2, '0')}`

  return (
    <main className="fx-paper fx-cloud min-h-screen pb-28 page-enter">
      <PageHeader title="收银台" backTo={order?.profileId ? `/order?profileId=${order.profileId}` : '/'} />

      <div className="p-4 space-y-3 pb-6">
        {/* 订单支付卡 — 严格原型 */}
        <div className="card-guofeng p-4 text-center">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/30 bg-amber-500/15 px-2.5 py-1 text-xs text-amber-200">
            <span className="size-1.5 shrink-0 animate-pulse rounded-full bg-amber-400" aria-hidden="true" />
            订单待支付 · <span className="font-mono font-bold">{countdownText}</span> 后自动关闭
          </div>
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
              <p className="mt-1 text-sm text-fg-secondary">姻缘完整报告已解锁，立即查看吧</p>
              <Link to={`/report/${orderNo}`} className="mt-6 w-full max-w-[280px]">
                <Button size="lg" variant="gold" className="w-full rounded-full text-base font-bold">
                  查看完整报告
                </Button>
              </Link>
            </div>
          ) : showH5 ? (
            <div className="flex flex-col items-center py-4 text-center">
              <p className="text-sm leading-relaxed text-fg-secondary">
                将拉起微信完成支付
                <br />
                支付成功后自动返回本页查看报告
              </p>
              <a href={effectivePayUrl!} target="_blank" rel="noopener noreferrer" className="mt-6 w-full max-w-[280px]">
                <Button size="lg" className="w-full rounded-full text-base font-bold">
                  点击唤起微信支付
                </Button>
              </a>
              <p className="mt-3 text-xs text-muted">未自动跳转？请点击右上角在浏览器中打开</p>
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
