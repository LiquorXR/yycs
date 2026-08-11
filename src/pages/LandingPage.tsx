import { Link } from 'react-router-dom'

function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-50">
      <h1 className="text-3xl font-bold text-slate-900">振凡命理</h1>
      <p className="text-slate-600">快手磁力智投 · 姻缘测算 H5 落地页</p>
      <Link
        to="/calc"
        className="rounded-full bg-rose-500 px-8 py-3 text-white hover:bg-rose-600"
      >
        开始测算
      </Link>
    </main>
  )
}

export default LandingPage
