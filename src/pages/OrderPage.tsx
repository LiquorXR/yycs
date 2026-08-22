import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Card } from '@/components/ui/card'
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

function AlipayIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 1024 1024" className={className} aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M342.280574 695.964872c-12.17939-0.373507-91.185792-5.564739-89.660042-75.386968l-0.002047 0c0.466628-21.243837 23.969924-78.636988 115.013477-69.206198 48.084135 4.979408 102.258988 34.075073 112.922862 39.21514 10.660804 5.140067 21.517059 10.758018 32.559557 16.85283-1.52268 1.52268-3.047406 2.953262-4.571109 4.285606-1.521656 1.333368-42.828434 40.181141-68.153216 55.226812C415.061181 681.995719 382.54051 697.200002 342.280574 695.964872zM883.155205 679.096692c-138.393977-22.093181-269.502014-84.801385-269.502014-84.801385 17.137309-22.086018 30.943756-43.605124 41.417295-64.551178 10.471492-20.944008 18.376533-39.603996 23.706935-55.976896 6.404873-18.835997 10.936073-36.732599 13.614066-53.702086l0.092098 0 0-0.568958c-0.026606 0.186242-0.062422 0.378623-0.092098 0.568958L559.387263 420.065148l0-63.406099 167.377078 0 0-27.42256L559.387263 329.23649l0-65.696258-43.988864 0c-7.231705 0-13.712303 0.573051-19.420305 1.719154-4.951779 0.759293-9.332553 2.185782-13.139252 4.281513-3.810792 2.095731-5.712095 4.855588-5.712095 8.284687l0 51.40988L314.319755 329.235466l0 27.42256 162.80597 0 0 63.406099L360.018563 420.064125l0 27.42256 247.926626 0c-0.765433 3.045359-2.474354 8.378831-5.142114 15.992229-2.665713 7.617491-6.478552 17.043165-11.426237 28.282137-4.951779 11.234879-11.236925 23.609721-18.854417 37.130665-7.614421 13.515828-16.941857 27.321252-27.990494 41.415248-5.329379-1.905396-10.469446-3.809769-15.421224-5.712095-4.952802-1.905396-9.716292-3.810792-14.281261-5.712095-11.42419-4.952802-23.51967-10.091846-36.277228-15.427364-12.756535-5.330402-26.27748-10.279111-40.558741-14.852266-14.281261-4.568039-29.228695-8.471952-44.846394-11.710716-15.613606-3.236718-31.79924-5.233188-48.555879-5.995551-17.135262-0.760317-34.180474 1.332345-51.125401 6.28003-16.944927 4.952802-32.373315 12.187577-46.272883 21.712511-13.901615 9.518794-25.233708 21.135366-33.993209 34.847669-8.755408 13.712303-13.326517 28.942169-13.70821 45.702901 0 19.419282 4.002151 36.46347 11.998265 51.123354 7.995091 14.661931 18.853393 26.850531 32.559557 36.559661 13.71128 9.711176 29.800723 17.044188 48.273447 21.991874 18.4717 4.952802 38.176484 7.43125 59.123562 7.43125l9.142218 0c1.140986 0 2.095731-0.194428 2.855024-0.573051 7.995091-0.382717 18.092054-1.239224 30.277584-2.570545 12.184507-1.338485 26.370601-4.571109 42.559305-9.711176 16.184611-5.14723 34.353412-12.567223 53.696969-23.711028 22.023596-12.691043 82.544994-61.122079 82.544994-61.122079 121.56059 54.002938 200.716394 86.878696 275.251971 103.09503-73.336262 106.876146-196.36632 176.98183-335.774393 176.98183-224.74567 0-406.938176-182.190459-406.938176-406.937153S287.255353 105.062847 512 105.062847s406.937153 182.190459 406.937153 406.937153C918.938176 571.551304 906.141732 628.117624 883.155205 679.096692z"
        fill="#1296db"
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
          <div className="overflow-hidden rounded-[16px] border border-border-gold bg-surface-card shadow-card">
              <div className="border-b border-border bg-gradient-to-b from-[#5a0f0f]/60 to-transparent px-5 py-4">
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
                      {displayName} {isRecommend ? <span className="ml-1 rounded bg-gold px-1.5 py-0.5 text-[10px] font-bold text-[#3a0a0a]">推荐</span> : null}
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

        {/* 支付方式 — 严格原型 */}
        <div className="card-guofeng p-4">
          <div className="mb-2.5 text-xs font-semibold tracking-widest text-gold-light">支付方式</div>
          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => setPayMethod('wechat')}
              className={`flex h-11 items-center justify-center gap-2 rounded-2xl border text-[13px] font-medium transition-colors [touch-action:manipulation] ${payMethod === 'wechat' ? 'border-[#2b7a63] bg-[#2b7a63]/15 text-gold-light' : 'border-white/10 bg-black/20 text-muted hover:border-gold/30'}`}
            >
              <WechatPayIcon className="size-5 shrink-0" /> 微信支付
            </button>
            <button
              type="button"
              disabled
              title="支付宝通道建设中，敬请期待"
              aria-disabled="true"
              className="flex h-11 items-center justify-center gap-2 rounded-2xl border border-white/10 bg-black/20 text-[13px] text-muted opacity-50 cursor-not-allowed [touch-action:manipulation]"
            >
              <AlipayIcon className="size-5 shrink-0" /> 支付宝
              <span className="ml-1 rounded bg-white/10 px-1 py-0.5 text-[10px] leading-none text-muted">建设中</span>
            </button>
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
