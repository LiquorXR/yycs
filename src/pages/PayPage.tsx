import { Link, useParams } from 'react-router-dom'

function PayPage() {
  const { orderNo } = useParams()

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-50">
      <h1 className="text-2xl font-bold text-slate-900">支付</h1>
      <p className="text-slate-600">支付页（占位，待开发）</p>
      <p className="text-sm text-slate-400">订单号: {orderNo}</p>
      <Link to={`/report/${orderNo}`} className="text-rose-500 underline">
        支付成功后查看报告
      </Link>
    </main>
  )
}

export default PayPage
