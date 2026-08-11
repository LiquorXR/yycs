import { Link } from 'react-router-dom'

function CalcPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-50">
      <h1 className="text-2xl font-bold text-slate-900">姻缘测算</h1>
      <p className="text-slate-600">测算页（占位，待开发）</p>
      <Link to="/order?profileId=demo" className="text-rose-500 underline">
        下一步：下单
      </Link>
    </main>
  )
}

export default CalcPage
