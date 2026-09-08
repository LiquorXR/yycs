import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Card } from '@/components/ui/card'
import { WechatPayIcon } from '@/components/ui/pay-icons'
import PageHeader from '@/components/PageHeader'
import { getProfilePreview, newIdempotencyKey, type ProfilePreview } from '@/api/profiles'
import { getProducts, type Product } from '@/api/products'
import { createOrder } from '@/api/orders'
import { formatPrice } from '@/lib/format'

function SkeletonCard() {
  return (
    <Card className="p-5 overflow-hidden relative" aria-hidden="true">
      <div className="shimmer absolute inset-0 opacity-40" aria-hidden="true" />
      <div className="relative h-4 w-2/5 rounded bg-gold/15" />
      <div className="relative mt-4 h-3 w-4/5 rounded bg-gold/10" />
      <div className="relative mt-2 h-3 w-3/5 rounded bg-gold/10" />
      <div className="relative mt-4 h-10 w-full rounded-lg bg-gold/10" />
    </Card>
  )
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="4" y="11" width="16" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  )
}

const MASK_LINES = [0.8, 0.66, 0.92, 0.6, 0.85, 0.58, 0.78, 0.72]

function MissingProfile() {
  return (
    <main className="flex min-h-screen flex-col text-fg">
      <PageHeader title="确认订单" backTo="/" />
      <div className="flex flex-1 flex-col items-center justify-center px-8 pb-20 text-center">
        <span className="font-kai text-4xl text-gold/40" aria-hidden="true">
          囍
        </span>
        <h1 className="mt-4 font-kai text-xl font-bold text-gold-light">未获取到姻缘测算信息</h1>
        <p className="mt-2 max-w-[260px] text-sm leading-relaxed text-fg-secondary">
          请先完成生辰姻缘测算，再回到此页确认订单。
        </p>
        <Link to="/calc" className="mt-8 w-full max-w-[260px]">
          <button type="button" className="btn-guofeng-primary h-12 w-full rounded-full text-base font-bold">
            去测姻缘
          </button>
        </Link>
      </div>
    </main>
  )
}

export default function OrderPage() {
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
    void (async () => {
      try {
        const res = await getProfilePreview(profileId)
        if (active) setPreview(res)
      } catch (err) {
        if (active)
          setPreviewError(err instanceof Error && err.message ? err.message : '获取测算信息失败，请稍后重试')
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
    void (async () => {
      try {
        const list = await getProducts({ type: 1 })
        if (active) setProducts(list)
      } catch (err) {
        if (active)
          setProductsError(err instanceof Error && err.message ? err.message : '产品加载失败，请稍后重试')
      }
    })()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (selected === null && products.length > 0) {
      const first = products.find((p) => p.status !== 0) ?? products[0]
      setSelected(first)
    }
  }, [products, selected])

  const adParams = (() => {
    const pattern = /^[a-zA-Z0-9_-]{1,64}$/
    const entries = (['ad_id', 'creative_id', 'campaign_id'] as const)
      .map((k) => [k, searchParams.get(k)])
      .filter(([, v]) => Boolean(v) && pattern.test(v as string)) as [string, string][]
    return entries.length > 0 ? Object.fromEntries(entries) : undefined
  })()

  const handleSubmit = async () => {
    if (!profileId || !selected) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const paymentMethod = 'h5'
      const res = await createOrder(
        { profileId, productId: selected.id, paymentMethod, adParams },
        newIdempotencyKey(),
      )
      navigate(`/pay/${res.orderNo}`, { state: { payType: res.payType, payChannel: res.payChannel ?? paymentMethod, payUrl: res.payUrl, codeUrl: res.codeUrl, wxJumpUrl: res.wxJumpUrl ?? null } })
    } catch (err) {
      setSubmitError(err instanceof Error && err.message ? err.message : '提交失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  if (!profileId) return <MissingProfile />

  return (
    <main className="fx-paper fx-cloud min-h-screen pb-28 page-enter">
      <PageHeader title="确认订单" backTo="/calc" />

      <div className="p-4 space-y-3 pb-6">
        {/* 测算信息预览 — 严格原型 */}
        {loading ? (
          <div className="space-y-2.5" aria-label="加载中">
            <div className="h-16 rounded-[16px] bg-gold/10 animate-pulse" />
            <div className="h-24 rounded-[16px] bg-gold/10 animate-pulse" />
          </div>
        ) : previewError ? (
          <p className="rounded-lg border border-red/25 bg-red/10 px-4 py-3 text-sm text-red-light" role="alert">
            {previewError}
          </p>
        ) : (
          <div className="overflow-hidden rounded-[16px] border border-border-gold bg-surface-card shadow-card">
              <div className="border-b border-border bg-gradient-to-b from-surface/60 to-transparent px-5 py-4">
                <p className="text-xs tracking-[0.3em] text-muted">姻缘测算 · 正缘预览</p>
                <h3 className="mt-1 font-kai text-lg font-bold text-gold-light">
                  {preview?.previewReport.title ?? '姻缘正缘测算预览'}
                </h3>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-fg-secondary">
                  <div className="flex items-center gap-1.5">
                    姻缘契合度：<span className="font-bold text-gold">★★★★☆</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    正缘桃花期：<span className="font-bold text-gold">今明两年</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    婚后走势：<span className="font-bold text-gold">稳步向好</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    相处之道：<span className="font-bold text-gold">已洞察</span>
                  </div>
                </div>
              </div>
              <div className="relative px-5 py-6">
                <div aria-hidden="true" className="space-y-2.5 blur-sm select-none">
                  {MASK_LINES.map((w, i) => (
                    <div
                      key={i}
                      className={`h-2.5 rounded-sm ${i % 3 === 0 ? 'bg-gold/20' : 'bg-gold/10'}`}
                      style={{ width: `${w * 100}%` }}
                    />
                  ))}
                </div>
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-bg/60 px-6 text-center backdrop-blur-[1px]">
                  <span className="flex size-14 items-center justify-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#591010] shadow-[0_0_20px_rgba(226,180,95,0.6)]">
                    <LockIcon className="size-7" />
                  </span>
                  <p className="mt-3 font-kai text-base font-bold text-gold-light">完整版需付费解锁</p>
                  <p className="mt-1 text-xs leading-relaxed text-fg-secondary">
                    解锁后可查看完整姻缘天书与
                    <br />
                    正缘专属指引
                  </p>
                </div>
              </div>
              <p className="border-t border-border px-5 pt-3 pb-4 text-center text-xs text-muted">
                报告编号：{profileId}
              </p>
            </div>
        )}

        {/* 产品选择 — 严格原型 */}
        <div className="space-y-2.5">
          <div className="text-xs tracking-widest text-gold/80">选择姻缘测算深度</div>
          {loading || (products.length === 0 && !productsError) ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : productsError ? (
            <p className="rounded-lg border border-red/25 bg-red/10 px-4 py-3 text-sm text-red-light" role="alert">
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
              const isRecommend = p.id === products[0]?.id
              // 兼容旧数据：单人测算报告 → 姻缘测算·正缘完整报告
              const displayName = p.name.includes('单人测算')
                ? p.name.replace('单人测算报告（免费版）', '姻缘测算·正缘预览（免费版）').replace('单人测算报告', '姻缘测算·正缘完整报告')
                : p.name
              const isYinyuan = displayName.includes('姻缘')
              return (
                <label
                  key={p.id}
                  className={`pressable will-change-transform flex cursor-pointer items-center gap-3 rounded-[16px] border p-3.5 text-left transition-all [touch-action:manipulation] ${
                    active ? 'border-gold bg-gold/8 ring-1 ring-gold shadow-gold' : 'border-border-gold bg-surface-card shadow-card hover:border-gold/50'
                  } ${disabled ? 'opacity-50' : ''}`}
                >
                  <input type="radio" name="product" checked={active} disabled={disabled} onChange={() => setSelected(p)} className="accent-gold" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                      <div className="font-kai text-[14px] font-semibold text-gold-light">
                      {displayName} {isRecommend ? <span className="ml-1 rounded bg-gold px-1.5 py-0.5 text-[10px] font-bold text-bg">推荐</span> : null}
                    </div>
                    <div className="truncate text-[11px] text-muted">{isYinyuan ? '含正缘画像/桃花年份/婚后走势/相处锦囊 + 大师亲批' : '需补充另一半信息 · 合婚指数'}</div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="font-bold text-gold">{formatPrice(p.price)}</div>
                    <div className="text-[11px] text-muted line-through">{formatPrice(Math.round(p.price * 2))}</div>
                  </div>
                </label>
              )
            })
          )}
        </div>

        {/* 支付方式：微信小店 H5 单链路，仅微信支付 */}
        <div className="card-guofeng p-4">
          <div className="mb-2.5 text-xs font-semibold tracking-widest text-gold-light">支付方式</div>
          <div className="flex h-11 items-center justify-center gap-2 rounded-2xl border border-[#2b7a63] bg-[#2b7a63]/15 text-[13px] font-medium text-gold-light">
            <WechatPayIcon className="size-5 shrink-0" />
            微信支付
          </div>
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-muted">实付金额</span>
            <span className="text-[18px] font-bold text-gold">{selected ? formatPrice(selected.price) : '¥9.9'}</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!selected || submitting || loading || Boolean(productsError)}
          className="btn-guofeng-primary h-[50px] w-full font-kai text-[17px] font-bold disabled:opacity-60"
        >
          {submitting ? '提交中…' : `立即解锁 · 支付 ${selected ? formatPrice(selected.price) : '¥9.9'}`}
        </button>
        <p className="text-center text-[10px] leading-relaxed text-white/40">
          支付即视为同意自动解锁报告（见{' '}
          <Link to="/privacy" className="text-white/60 underline decoration-white/20 underline-offset-2 hover:text-gold">
            隐私政策
          </Link>
          ）
        </p>

        {submitError ? (
          <p className="rounded-lg border border-red/25 bg-red/10 px-4 py-3 text-sm text-red-light" role="alert">
            {submitError}
          </p>
        ) : null}
      </div>
    </main>
  )
}
