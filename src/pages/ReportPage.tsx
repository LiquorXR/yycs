import { Link, useParams } from 'react-router-dom'

function ReportPage() {
  const { orderNo } = useParams()

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-50">
      <h1 className="text-2xl font-bold text-slate-900">姻缘报告</h1>
      <p className="text-slate-600">报告页（占位，待开发）</p>
      <p className="text-sm text-slate-400">订单号: {orderNo}</p>
      <Link to="/" className="text-rose-500 underline">
        返回首页
      </Link>
    </main>
  )
}

export default ReportPage
