import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Huiwen } from '@/components/decor/Huiwen'
import PageHeader from '@/components/PageHeader'
import { getOrderReport, type OrderReport } from '@/api/orders'

/** 已解锁（完整报告可用）的订单状态 */
const UNLOCKED_STATES = ['UNLOCKED', 'DELIVERED', 'ADDED_WECOM']

/** 轮询间隔：5s */
const POLL_INTERVAL = 5000

function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="4" y="11" width="16" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  )
}

function isUnlocked(report: OrderReport): boolean {
  return UNLOCKED_STATES.includes(report.state) || report.report.locked === false
}

/** 企微活码区：二维码 + 添加到企业微信 + 人工测算说明 */
function WecomSection({ wecom }: { wecom: NonNullable<OrderReport['wecom']> }) {
  return (
    <section className="mt-8" aria-label="添加企业微信">
      <div className="flex items-center gap-2">
        <Huiwen className="h-2 w-8 text-ink/30" />
        <h2 className="font-serif text-lg font-bold text-ink">人工深度测算</h2>
      </div>

      <Card className="mt-3 overflow-hidden border-ink/10">
        <div className="flex flex-col items-center border-b border-ink/10 bg-paper-deep/50 px-5 py-6 text-center">
          <img
            src={wecom.qrcodeUrl}
            alt="企业微信活码二维码"
            className="size-44 rounded-lg border border-ink/15 bg-white object-contain shadow-card"
            loading="lazy"
          />
          <a href="wecom://" className="mt-5 w-full max-w-[280px]">
            <Button size="lg" variant="gold" className="w-full rounded-full text-base font-bold">
              添加到企业微信
            </Button>
          </a>
          <p className="mt-2 font-serif text-xs text-ink-faint">
            未唤起企业微信？请长按上方二维码识别添加
          </p>
        </div>
        <p className="px-5 py-4 font-serif text-sm leading-relaxed text-ink-soft">
          {wecom.note ??
            '支付成功后，专属命理师将通过企业微信与您联系，结合您的生辰信息进行一对一深度测算与答疑。'}
        </p>
      </Card>
    </section>
  )
}

function ReportPage() {
  const { orderNo = '' } = useParams()
  const [report, setReport] = useState<OrderReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const inFlightRef = useRef(false)
  const loadedRef = useRef(false)

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

  const unlocked = report ? isUnlocked(report) : false
  const reportTitle = report?.report.title
  const lockedNote = report?.report.lockedNote ?? '完整版需付费解锁'

  return (
    <main className="min-h-screen pb-20 text-ink">
      <PageHeader title="姻缘报告" backTo="/" />

      <div className="px-5 pt-6">
        {/* 加载态 */}
        {loading ? (
          <div className="animate-pulse space-y-4" aria-label="报告加载中">
            <div className="h-6 w-3/5 rounded bg-ink/15" />
            <div className="h-72 rounded-2xl bg-ink/8" />
            <div className="h-3 w-2/5 rounded bg-ink/10" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center px-6 py-14 text-center">
            <span className="flex size-16 items-center justify-center rounded-full bg-ink text-paper-light shadow-ink">
              <LockIcon className="size-8" />
            </span>
            <p className="mt-4 font-serif text-lg font-bold text-ink" role="alert">
              {error}
            </p>
            <p className="mt-2 font-serif text-sm text-ink-soft">
              报告可能尚未支付解锁，或订单不存在
            </p>
            <Link to={`/pay/${orderNo}`} className="mt-6 w-full max-w-[280px]">
              <Button size="lg" className="w-full rounded-full text-base font-bold">
                前往支付
              </Button>
            </Link>
            <Link to="/" className="mt-3 w-full max-w-[280px]">
              <Button variant="outline" className="w-full rounded-full">
                返回首页
              </Button>
            </Link>
          </div>
        ) : report ? (
          <>
            {/* 报告标题 */}
            <section aria-label="报告标题">
              <div className="flex items-center gap-2">
                <Huiwen className="h-2 w-8 text-ink/30" />
                <h2 className="font-serif text-lg font-bold text-ink">
                  {reportTitle ?? '合婚测算报告'}
                </h2>
                <Badge variant={unlocked ? 'gold' : 'outline'}>
                  {unlocked ? '已解锁' : '预览版'}
                </Badge>
              </div>
            </section>

            {/* 报告内容区 */}
            <section className="mt-3" aria-label="报告内容">
              <Card className="overflow-hidden border-ink/10">
                <div className="relative">
                  <iframe
                    src={report.report.contentUrl}
                    title={reportTitle ?? '测算报告'}
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    className={`h-[420px] w-full border-0 bg-white ${unlocked ? '' : 'blur-[6px]'}`}
                  />
                  {!unlocked ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-paper/55 px-6 text-center backdrop-blur-[2px]">
                      <span className="flex size-14 items-center justify-center rounded-full bg-ink text-paper-light shadow-ink">
                        <LockIcon className="size-7" />
                      </span>
                      <p className="mt-3 font-serif text-base font-bold text-ink">
                        {lockedNote}
                      </p>
                      <p className="mt-1 font-serif text-xs leading-relaxed text-ink-soft">
                        解锁后可查看完整合婚报告与
                        <br />
                        专属缘分建议
                      </p>
                      <Link to={`/pay/${orderNo}`} className="mt-4 w-full max-w-[220px]">
                        <Button size="lg" className="w-full rounded-full text-base font-bold">
                          去解锁
                        </Button>
                      </Link>
                    </div>
                  ) : null}
                </div>
              </Card>
            </section>

            {/* 企微活码区（未生成时隐藏） */}
            {report.wecom ? <WecomSection wecom={report.wecom} /> : null}

            <p className="mt-6 text-center font-serif text-xs text-ink-faint">
              报告编号：{report.orderNo}
            </p>
          </>
        ) : null}
      </div>
    </main>
  )
}

export default ReportPage
