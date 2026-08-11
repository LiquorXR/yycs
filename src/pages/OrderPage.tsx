import { Link, useSearchParams } from 'react-router-dom'

function OrderPage() {
  const [searchParams] = useSearchParams()
  const profileId = searchParams.get('profileId')

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-50">
      <h1 className="text-2xl font-bold text-slate-900">确认订单</h1>
      <p className="text-slate-600">下单页（占位，待开发）</p>
      <p className="text-sm text-slate-400">profileId: {profileId ?? '—'}</p>
      <Link to="/pay/ORDER202608110001" className="text-rose-500 underline">
        下一步：支付
      </Link>
    </main>
  )
}

export default OrderPage
