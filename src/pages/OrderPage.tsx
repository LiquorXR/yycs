import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Huiwen } from '@/components/decor/Huiwen'
import { DoubleHappiness } from '@/components/decor/Ornaments'
import PageHeader from '@/components/PageHeader'
import { getProfilePreview, newIdempotencyKey, type ProfilePreview } from '@/api/profiles'
import { getProducts, type Product } from '@/api/products'
import { createOrder } from '@/api/orders'
import { formatPrice, maskName, formatYearMonth } from '@/lib/format'

function SkeletonCard() {
  return (
    <Card className="animate-pulse p-5" aria-hidden="true">
      <div className="h-4 w-2/5 rounded bg-gold/15" />
      <div className="mt-4 h-3 w-4/5 rounded bg-gold/10" />
      <div className="mt-2 h-3 w-3/5 rounded bg-gold/10" />
      <div className="mt-4 h-10 w-full rounded-lg bg-gold/10" />
    </Card>
  )
}

/** 无 profileId 参数：引导回测算页 */
function MissingProfile() {
  return (
    <main className="flex min-h-screen flex-col text-fg">
      <PageHeader title="确认订单" backTo="/" />
      <div className="flex flex-1 flex-col items-center justify-center px-8 pb-20 text-center">
        <DoubleHappiness className="text-4xl text-gold/40" />
        <h1 className="mt-4 font-kai text-xl font-bold text-gold-light">
          未获取到测算信息
        </h1>
        <p className="mt-2 max-w-[260px] text-sm leading-relaxed text-fg-secondary">
          请先完成生辰信息测算，再回到此页确认订单。
        </p>
        <Link to="/calc" className="mt-8 w-full max-w-[260px]">
          <Button size="lg" className="w-full rounded-full text-base font-bold">
            去免费测算
          </Button>
        </Link>
      </div>
    </main>
  )
}

function OrderPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const profileId = searchParams.get('profileId')

  const [preview, setPreview] = useState<ProfilePreview | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [productsError, setProductsError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Product | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    if (!profileId) return
    let active = true
    ;(async () => {
      try {
        const res = await getProfilePreview(profileId)
        if (active) setPreview(res)
      } catch (err) {
        if (active) {
          setPreviewError(
            err instanceof Error && err.message ? err.message : '获取测算信息失败，请稍后重试',
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    })()
    return () => {
      active = false
    }
  }, [profileId])

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const list = await getProducts({ type: 1 })
        if (active) setProducts(list)
      } catch (err) {
        if (active) {
          setProductsError(
            err instanceof Error && err.message ? err.message : '产品加载失败，请稍后重试',
          )
        }
      }
    })()
    return () => {
      active = false
    }
  }, [])

  // 默认选中第一个启用产品
  useEffect(() => {
    if (selected === null && products.length > 0) {
      const first = products.find((p) => p.status !== 0) ?? products[0]
      setSelected(first)
    }
  }, [products, selected])

  const adParams = (() => {
    const entries = (['ad_id', 'creative_id', 'campaign_id'] as const)
      .map((k) => [k, searchParams.get(k)])
      .filter(([, v]) => Boolean(v)) as [string, string][]
    return entries.length > 0 ? Object.fromEntries(entries) : undefined
  })()

  const handleSubmit = async () => {
    if (!profileId || !selected) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await createOrder(
        {
          profileId,
          productId: selected.id,
          paymentMethod: 'auto',
          adParams,
        },
        newIdempotencyKey(),
      )
      navigate(`/pay/${res.orderNo}`, {
        state: { payType: res.payType, payUrl: res.payUrl, codeUrl: res.codeUrl },
      })
    } catch (err) {
      setSubmitError(
        err instanceof Error && err.message ? err.message : '提交失败，请稍后重试',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (!profileId) return <MissingProfile />

  const summaryRows: { label: string; value: string | undefined }[] = [
    { label: '甲方', value: preview?.nameA ? `${maskName(preview.nameA)} ${formatYearMonth(preview.birthA ?? '')}` : undefined },
    { label: '乙方', value: preview?.nameB ? `${maskName(preview.nameB)} ${formatYearMonth(preview.birthB ?? '')}` : undefined },
  ]

  return (
    <main className="fx-paper fx-cloud fade-in min-h-screen pb-28">
      <PageHeader title="确认订单" backTo="/calc" />

      <div className="px-5 pt-6">
        {/* 测算信息摘要 */}
        <section aria-label="测算信息摘要">
          <div className="flex items-center gap-2">
            <Huiwen className="h-2 w-8 text-gold/40" />
            <h2 className="font-kai text-lg font-bold text-gold-light">测算信息</h2>
          </div>

          <Card className="mt-3">
            <CardContent className="p-5">
              {loading ? (
                <div className="space-y-2.5" aria-label="加载中">
                  <div className="h-3.5 w-3/4 animate-pulse rounded bg-gold/10" />
                  <div className="h-3 w-1/2 animate-pulse rounded bg-gold/10" />
                </div>
              ) : previewError ? (
                <p className="text-sm text-red-light" role="alert">
                  {previewError}
                </p>
              ) : (
                <>
                  <h3 className="font-kai text-base font-bold text-gold-light">
                    {preview?.previewReport.title ?? '合婚测算报告'}
                  </h3>
                  <div className="mt-3 space-y-1.5 text-sm text-fg/85">
                    {summaryRows.some((r) => r.value) ? (
                      summaryRows.map(
                        (r) =>
                          r.value && (
                            <p key={r.label} className="flex gap-2">
                              <span className="shrink-0 text-muted">{r.label}</span>
                              <span>{r.value}</span>
                            </p>
                          ),
                      )
                    ) : (
                      <p className="text-fg-secondary">
                        信息已加密保护，仅展示脱敏摘要
                      </p>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </section>

        {/* 产品选择 */}
        <section className="mt-8" aria-label="选择服务套餐">
          <div className="flex items-center gap-2">
            <Huiwen className="h-2 w-8 text-gold/40" />
            <h2 className="font-kai text-lg font-bold text-gold-light">服务套餐</h2>
          </div>

          <div className="mt-3 space-y-3">
            {loading || (products.length === 0 && !productsError) ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : productsError ? (
              <p
                className="rounded-lg border border-red/25 bg-red/10 px-4 py-3 text-sm text-red-light"
                role="alert"
              >
                {productsError}
              </p>
            ) : products.length === 0 ? (
              <p className="rounded-xl border border-border-gold bg-surface-card px-4 py-5 text-center text-sm text-fg-secondary shadow-card">
                暂无付费服务套餐，敬请期待
              </p>
            ) : (
              products.map((p) => {
                const disabled = p.status === 0
                const active = selected?.id === p.id
                return (
                  <button
                    key={p.id}
                    type="button"
                    disabled={disabled}
                    aria-pressed={active}
                    onClick={() => setSelected(p)}
                    className={`w-full rounded-2xl border text-left transition-all ${
                      active
                        ? 'border-gold bg-gold/10 shadow-gold'
                        : 'border-border-gold bg-surface-card shadow-card hover:border-gold/60'
                    } ${disabled ? 'opacity-50' : ''}`}
                  >
                    <div className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-3">
                        <span
                          className={`flex size-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
                            active ? 'border-gold bg-gold' : 'border-gold/40'
                          }`}
                          aria-hidden="true"
                        >
                          {active ? (
                            <svg viewBox="0 0 24 24" className="size-3 text-[#591010]" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M5 12l4.5 4.5L19 7" />
                            </svg>
                          ) : null}
                        </span>
                        <span className="font-kai text-base font-bold text-fg">
                          {p.name}
                        </span>
                      </div>
                      <span className="font-kai text-xl font-bold text-gold">
                        {formatPrice(p.price)}
                      </span>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </section>

        {submitError ? (
          <p
            className="mt-6 rounded-lg border border-red/25 bg-red/10 px-4 py-3 text-sm text-red-light"
            role="alert"
          >
            {submitError}
          </p>
        ) : null}
      </div>

      {/* 底部固定提交栏 */}
      <div className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-border-gold bg-[#2e0808]/96 backdrop-blur-md">
        <div className="flex items-center justify-between gap-4 px-5 py-3">
          <div>
            <p className="text-xs text-muted">合计金额</p>
            <p className="font-kai text-xl font-bold text-gold">
              {selected ? formatPrice(selected.price) : '¥0.00'}
              <span className="ml-1 text-xs font-normal text-muted">
                一次解锁 · 永久查看
              </span>
            </p>
          </div>
          <Button
            size="lg"
            className="w-36 shrink-0 rounded-full text-base font-bold"
            disabled={!selected || submitting || loading || Boolean(productsError)}
            onClick={handleSubmit}
          >
            {submitting ? (
              <>
                <svg
                  className="size-5 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
                </svg>
                提交中…
              </>
            ) : (
              '提交订单'
            )}
          </Button>
        </div>
      </div>
    </main>
  )
}

export default OrderPage
