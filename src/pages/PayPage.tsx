import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Huiwen } from '@/components/decor/Huiwen'
import PageHeader from '@/components/PageHeader'
import { getOrder, type OrderDetail } from '@/api/orders'
import { formatPrice } from '@/lib/format'

/** 下单页跳转时携带的支付参数（页面刷新后回退为订单 payType 空态） */
interface PayState {
  payType: string | null
  payUrl: string | null
  codeUrl: string | null
}

const STATE_LABEL: Record<string, string> = {
  CREATED: '待支付',
  PAID: '已支付',
  UNLOCKED: '已解锁',
  DELIVERED: '已交付',
  ADDED_WECOM: '已完成',
  CLOSED: '已关闭',
  REFUNDING: '退款中',
  REFUNDED: '已退款',
}

/** Native 扫码占位：轻量渲染，不引入二维码库 */
function NativeQrArea({ codeUrl }: { codeUrl: string }) {
  return (
    <div className="flex flex-col items-center">
      <div className="relative flex size-52 items-center justify-center rounded-xl border-2 border-dashed border-gold/60 bg-white p-4 shadow-card">
        <svg viewBox="0 0 100 100" className="size-full" aria-hidden="true">
          <rect x="6" y="6" width="34" height="34" fill="none" stroke="#2b2b2b" strokeWidth="5" />
          <rect x="60" y="6" width="34" height="34" fill="none" stroke="#2b2b2b" strokeWidth="5" />
          <rect x="6" y="60" width="34" height="34" fill="none" stroke="#2b2b2b" strokeWidth="5" />
          <path d="M16 16h14v14H16z M70 16h14v14H70z M16 70h14v14H16z" fill="#2b2b2b" />
          <path d="M10 46h10v5H10z M10 60h5v5H10z M20 50h5v10h-5z M34 44h8v4h-8z M38 54h6v6h-6z M52 12h6v4h-6z M58 20h8v8h-8z M52 30h5v6h-5z M64 10h4v6h-4z M46 52h6v4h-6z M56 56h4v4h-4z M52 70h10v6h-10z M70 54h8v6h-8z M66 44h4v6h-4z M80 40h6v8h-6z M80 54h6v5h-6z M46 70h4v6h-4z" fill="#2b2b2b" />
        </svg>
        <span className="absolute bottom-2 right-2 rounded bg-paper/90 px-1.5 py-0.5 text-[10px] text-cinnabar">
          长按保存
        </span>
      </div>
      <p className="mt-4 text-sm text-ink/60">长按二维码保存到相册，打开微信「扫一扫」完成支付</p>
      <p className="mt-1 text-xs text-ink/45">
        长按识别失败？请复制下方链接在微信中打开
      </p>
      <p className="mt-2 w-full max-w-[300px] break-all rounded-lg bg-gold-pale/50 px-3 py-2 text-xs text-ink/60 select-all">
        {codeUrl}
      </p>
    </div>
  )
}

/** 支付通道未就绪的空态 */
function PayChannelEmpty() {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <span className="flex size-16 items-center justify-center rounded-full bg-gold-pale text-gold-dark">
        <svg viewBox="0 0 24 24" className="size-8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="6" width="18" height="13" rx="2.5" />
          <path d="M3 10h18M7 15h4" />
        </svg>
      </span>
      <p className="mt-5 font-kai text-lg font-bold text-crimson">
        支付通道即将上线，敬请期待
      </p>
      <p className="mt-2 text-sm leading-relaxed text-ink/55">
        支付功能正在建设中，完成后即可解锁完整报告
      </p>
    </div>
  )
}

function PayPage() {
  const { orderNo = '' } = useParams()
  const location = useLocation()
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
        setError(
          err instanceof Error && err.message ? err.message : '订单信息加载失败，请稍后重试',
        )
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

  const pay = (location.state as PayState | null) ?? null

  const stateLabel = order ? (STATE_LABEL[order.state] ?? order.state) : ''
  const isPaid = order?.state === 'PAID'
  const showH5 = pay?.payType === 'h5' && Boolean(pay.payUrl)
  const showNative = pay?.payType === 'native' && Boolean(pay.codeUrl)
  const showEmpty = !showH5 && !showNative

  return (
    <main className="min-h-screen bg-paper pb-28 text-ink">
      <PageHeader
        title="订单支付"
        backTo={order?.profileId ? `/order?profileId=${order.profileId}` : '/'}
      />

      <div className="px-5 pt-6">
        {/* 订单金额卡 */}
        <Card className="overflow-hidden border-gold/40">
          <div className="bg-gradient-to-r from-crimson to-cinnabar px-5 py-6 text-center">
            <p className="text-xs tracking-[0.25em] text-paper/80">应付金额</p>
            <p className="mt-1 font-kai text-[2.2rem] leading-none font-bold text-gold-grad">
              {order ? formatPrice(order.amount) : '¥0.00'}
            </p>
            <div className="mt-3 flex items-center justify-center gap-2">
              <Badge variant="gold">{stateLabel || '…'}</Badge>
              <span className="font-mono text-xs text-paper/70">{order?.orderNo ?? orderNo}</span>
            </div>
          </div>
        </Card>

        {/* 支付方式区 */}
        <section className="mt-6" aria-label="支付方式">
          <div className="flex items-center gap-2">
            <Huiwen className="h-2 w-8 text-gold/80" />
            <h2 className="font-kai text-lg font-bold text-crimson">微信支付</h2>
          </div>

          <Card className="mt-3 border-gold/40">
            <CardContent className="p-5">
              {loading ? (
                <div className="animate-pulse space-y-3 py-6" aria-label="加载中">
                  <div className="mx-auto h-8 w-40 rounded bg-ink/10" />
                  <div className="mx-auto h-3 w-56 rounded bg-ink/10" />
                </div>
              ) : error ? (
                <div className="flex flex-col items-center py-6 text-center">
                  <p className="text-sm text-cinnabar" role="alert">
                    {error}
                  </p>
                  <Button variant="outline" className="mt-4" onClick={() => void fetchOrder()}>
                    重新加载
                  </Button>
                </div>
              ) : isPaid ? (
                <div className="flex flex-col items-center py-6 text-center">
                  <span className="flex size-16 items-center justify-center rounded-full bg-gradient-to-b from-gold-bright to-gold text-white shadow-gold">
                    <svg viewBox="0 0 24 24" className="size-8" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M5 12l4.5 4.5L19 7" />
                    </svg>
                  </span>
                  <p className="mt-4 font-kai text-lg font-bold text-crimson">支付成功</p>
                  <p className="mt-1 text-sm text-ink/55">完整报告已解锁，立即查看吧</p>
                  <Link to={`/report/${orderNo}`} className="mt-6 w-full max-w-[280px]">
                    <Button size="lg" variant="gold" className="w-full rounded-full text-base font-bold">
                      查看完整报告
                    </Button>
                  </Link>
                </div>
              ) : showH5 ? (
                <div className="flex flex-col items-center py-4 text-center">
                  <p className="text-sm leading-relaxed text-ink/60">
                    将拉起微信完成支付
                    <br />
                    支付成功后自动返回本页查看报告
                  </p>
                  <a href={pay!.payUrl!} className="mt-6 w-full max-w-[280px]">
                    <Button size="lg" className="w-full rounded-full text-base font-bold">
                      点击唤起微信支付
                    </Button>
                  </a>
                  <p className="mt-3 text-xs text-ink/45">
                    未自动跳转？请点击右上角在浏览器中打开
                  </p>
                </div>
              ) : showNative ? (
                <NativeQrArea codeUrl={pay!.codeUrl!} />
              ) : showEmpty ? (
                <PayChannelEmpty />
              ) : null}
            </CardContent>
          </Card>
        </section>

        {/* 未支付时的刷新引导 */}
        {!loading && !error && order && !isPaid && order.state === 'CREATED' && !showH5 && !showNative ? (
          <p className="mt-4 text-center text-xs text-ink/45">
            已支付？{' '}
            <button
              type="button"
              className="text-cinnabar underline underline-offset-2"
              onClick={() => void fetchOrder({ silent: true })}
            >
              刷新支付状态
            </button>
          </p>
        ) : null}
      </div>
    </main>
  )
}

export default PayPage
