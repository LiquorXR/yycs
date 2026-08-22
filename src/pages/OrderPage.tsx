import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Card } from '@/components/ui/card'
import PageHeader from '@/components/PageHeader'
import { getProfilePreview, newIdempotencyKey, type ProfilePreview } from '@/api/profiles'
import { getProducts, type Product } from '@/api/products'
import { createOrder } from '@/api/orders'
import { formatPrice, maskName, formatYearMonth } from '@/lib/format'

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

function MissingProfile() {
  return (
    <main className="flex min-h-screen flex-col text-fg">
      <PageHeader title="确认订单" backTo="/" />
      <div className="flex flex-1 flex-col items-center justify-center px-8 pb-20 text-center">
        <span className="font-kai text-4xl text-gold/40" aria-hidden="true">
          囍
        </span>
        <h1 className="mt-4 font-kai text-xl font-bold text-gold-light">未获取到测算信息</h1>
        <p className="mt-2 max-w-[260px] text-sm leading-relaxed text-fg-secondary">
          请先完成生辰信息测算，再回到此页确认订单。
        </p>
        <Link to="/calc" className="mt-8 w-full max-w-[260px]">
          <button type="button" className="btn-guofeng-primary h-12 w-full rounded-full text-base font-bold">
            去免费测算
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
  const [payMethod, setPayMethod] = useState<'wechat' | 'alipay'>('wechat')

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
    if (payMethod === 'alipay') {
      setSubmitError('支付宝通道建设中，请选择微信支付')
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      const paymentMethod = 'h5'
      const res = await createOrder(
        { profileId, productId: selected.id, paymentMethod, adParams },
        newIdempotencyKey(),
      )
      navigate(`/pay/${res.orderNo}`, { state: { payType: res.payType, payUrl: res.payUrl, codeUrl: res.codeUrl } })
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
          <>
            <div className="card-guofeng flex items-center gap-3 p-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-full border-2 border-gold bg-[radial-gradient(circle,#4a0e0e_0%,#2a0808_100%)] font-kai text-gold-light">
                命
              </span>
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-fg text-[14px]">
                  {preview?.name ? maskName(preview.name) : '命主'}{' '}
                  <span className="text-xs text-muted">{preview?.birth ? formatYearMonth(preview.birth) : ''}</span>
                </div>
                <div className="text-[11px] text-gold">已生成命盘预览 · 待解锁完整报告</div>
              </div>
              <span className="seal-mark shrink-0">待解锁</span>
            </div>

            <div className="rounded-[16px] border border-gold/20 bg-[#3a0a0a]/55 p-3 text-[12px] leading-relaxed text-fg-secondary">
              <div className="font-kai font-semibold text-gold-light mb-1">
                {preview?.previewReport.title ?? '命盘密签（节选）'}
              </div>
              <p className="line-clamp-3">{preview?.previewReport.lockedNote ?? '喜用神为火土，正缘桃花期集中在2026秋-2027春，婚后财运呈阶梯上扬，需留意2028年小耗…'}</p>
              <div className="mt-2 flex gap-1.5">
                <span className="rounded-full border border-gold/20 bg-gold/10 px-2 py-0.5 text-[11px] text-gold">四柱排盘 ✓</span>
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-muted">喜忌解锁后可见</span>
              </div>
            </div>
          </>
        )}

        {/* 产品选择 — 严格原型 */}
        <div className="space-y-2.5">
          <div className="text-xs tracking-widest text-gold/80">选择测算深度</div>
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
              const displayName = p.name.includes('姻缘测算')
                ? p.name.replace('姻缘测算完整报告', '单人测算报告').replace('姻缘测算免费版', '单人测算报告（免费版）').replace('姻缘测算', '单人测算报告')
                : p.name
              const isSingle = displayName.includes('单人')
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
                      {displayName} {isRecommend ? <span className="ml-1 rounded bg-gold px-1.5 py-0.5 text-[10px] font-bold text-[#3a0a0a]">推荐</span> : null}
                    </div>
                    <div className="truncate text-[11px] text-muted">{isSingle ? '含正缘/财运/性格/避坑 + 大师亲批' : '需补充另一半信息 · 合婚指数'}</div>
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

        {/* 支付方式 — 严格原型 */}
        <div className="card-guofeng p-4">
          <div className="mb-2.5 text-xs font-semibold tracking-widest text-gold-light">支付方式</div>
          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => setPayMethod('wechat')}
              className={`flex h-11 items-center justify-center gap-2 rounded-2xl border text-[13px] font-medium transition-colors [touch-action:manipulation] ${payMethod === 'wechat' ? 'border-[#2b7a63] bg-[#2b7a63]/15 text-gold-light' : 'border-white/10 bg-black/20 text-muted hover:border-gold/30'}`}
            >
              <span className="grid size-5 place-items-center rounded-full bg-[#07c160] text-[11px] font-bold text-white">微</span> 微信支付
            </button>
            <button
              type="button"
              disabled
              title="支付宝通道建设中，敬请期待"
              aria-disabled="true"
              className="flex h-11 items-center justify-center gap-2 rounded-2xl border border-white/10 bg-black/20 text-[13px] text-muted opacity-50 cursor-not-allowed [touch-action:manipulation]"
            >
              <span className="grid size-5 place-items-center rounded-full bg-[#1677ff] text-[11px] font-bold text-white">支</span> 支付宝
              <span className="ml-1 rounded bg-white/10 px-1 py-0.5 text-[10px] leading-none text-muted">建设中</span>
            </button>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-muted">实付金额</span>
            <span className="text-[18px] font-bold text-gold">{selected ? formatPrice(selected.price) : '¥29.90'}</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!selected || submitting || loading || Boolean(productsError)}
          className="btn-guofeng-primary h-[50px] w-full font-kai text-[17px] font-bold disabled:opacity-60"
        >
          {submitting ? '提交中…' : `立即解锁 · 支付 ${selected ? formatPrice(selected.price) : '¥29.90'}`}
        </button>
        <p className="text-center text-[10px] leading-relaxed text-white/40">
          支付即视为同意自动解锁报告 · 1年内可重复查看（见{' '}
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
