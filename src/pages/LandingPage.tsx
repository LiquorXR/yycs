import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Xiangyun } from '@/components/decor/Xiangyun'
import { Huiwen } from '@/components/decor/Huiwen'
import { DoubleHappiness, StarSeal } from '@/components/decor/Ornaments'

/* ---------------- 小部件 ---------------- */

function StarRow({ className }: { className?: string }) {
  return (
    <span className={className} aria-label="5 星好评" role="img">
      {Array.from({ length: 5 }).map((_, i) => (
        <svg
          key={i}
          viewBox="0 0 24 24"
          className="inline-block size-3.5 text-gold"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M12 1.8l3.1 6.3 7 1-5 4.9 1.2 6.9-6.3-3.3-6.3 3.3 1.2-6.9-5-4.9 7-1z" />
        </svg>
      ))}
    </span>
  )
}

function SectionHeading({
  eyebrow,
  title,
  sub,
}: {
  eyebrow: string
  title: string
  sub?: string
}) {
  return (
    <header className="flex flex-col items-center text-center">
      <span className="text-xs font-medium tracking-[0.35em] text-gold-dark uppercase">
        {eyebrow}
      </span>
      <h2 className="mt-2 font-kai text-[1.75rem] leading-snug font-bold text-crimson">
        {title}
      </h2>
      <Huiwen className="mt-3 w-36 text-gold/80" />
      {sub ? (
        <p className="mt-3 max-w-[300px] text-sm leading-relaxed text-ink/60">
          {sub}
        </p>
      ) : null}
    </header>
  )
}

function Seal({ char }: { char: string }) {
  return (
    <span
      aria-hidden="true"
      className="flex size-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-b from-gold-bright to-gold-dark font-kai text-xl text-white shadow-gold"
    >
      {char}
    </span>
  )
}

const FEATURES = [
  {
    seal: '婚',
    title: '生辰合婚解析',
    desc: '双方八字五行、生肖属相全面比对，合婚指数一目了然，一眼看透你的正缘走向。',
  },
  {
    seal: '运',
    title: '运势详细解读',
    desc: '姻缘流年、大运起伏逐项详解，抓住良缘出现的每一个关键时机。',
  },
  {
    seal: '师',
    title: '企微人工深度测算',
    desc: '资深命理师一对一深度测算，结合你的具体问题，人工答疑更贴心。',
  },
]

const TESTIMONIALS = [
  {
    name: '李**',
    tag: '已领证',
    text: '师傅测算得太准了，我和对象确实是性格互补才走到一起，现在顺利领证，感恩！',
  },
  {
    name: '王**',
    tag: '缘分已定',
    text: '免费预览就很有内容，人工深度测算更是一针见血，把我们的相处建议说得很明白。',
  },
  {
    name: '张**',
    tag: '会员用户',
    text: '报告很详细，客服也耐心，生辰信息有加密保障，用起来很放心，推荐给朋友了。',
  },
]

const STATS = [
  { num: '12,800+', label: '已完成测算' },
  { num: '98%', label: '好评率' },
  { num: '7×24h', label: '专属答疑' },
]

/* ---------------- 页面 ---------------- */

function LandingPage() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      {/* 第 1 屏：首屏 Hero */}
      <section className="relative flex min-h-[100dvh] flex-col overflow-hidden bg-gradient-to-b from-crimson via-cinnabar to-crimson text-paper">
        {/* 装饰祥云 */}
        <Xiangyun
          filled
          className="absolute -top-4 -left-14 w-44 text-gold-bright/25"
        />
        <Xiangyun className="absolute top-1/4 -right-12 w-36 rotate-6 text-paper/20" />
        <Xiangyun
          filled
          className="absolute -bottom-10 -left-16 w-48 text-paper/8"
        />

        <header className="pt-safe relative z-10">
          <div className="flex items-center justify-center gap-2.5 px-6 pt-4 pb-2">
            <Huiwen className="h-2 w-12 text-gold/80" />
            <span className="font-kai text-lg font-bold tracking-[0.35em] text-gold-grad">
              振凡命理
            </span>
            <Huiwen className="h-2 w-12 text-gold/80" />
          </div>
        </header>

        <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-7 text-center">
          <DoubleHappiness className="mb-5 text-4xl" />
          <h1 className="font-kai text-[2.9rem] leading-[1.18] font-bold">
            <span className="text-gold-grad">天生一对</span>
            <br />
            <span className="text-gold-grad">缘定三生</span>
          </h1>
          <p className="mt-5 text-base font-medium tracking-[0.45em] text-paper/95">
            八字合婚 · 缘分测算
          </p>

          <div className="mt-7 flex items-center gap-2.5 text-gold-bright/90">
            <Huiwen className="h-2 w-14" />
            <StarSeal className="size-2.5" />
            <Huiwen className="h-2 w-14" />
          </div>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-xs text-paper/80">
            {['免费出报告', '无需注册', '30 秒出结果'].map((t) => (
              <span key={t} className="flex items-center gap-1.5">
                <StarSeal className="size-2 text-gold-bright" />
                {t}
              </span>
            ))}
          </div>

          <div className="mt-10 w-full max-w-[300px]">
            <Link to="/calc" className="block">
              <Button
                variant="gold"
                size="xl"
                className="w-full rounded-full border border-gold-bright/60 text-lg font-bold"
              >
                免费测算
              </Button>
            </Link>
            <p className="mt-3 text-center text-xs text-paper/70">
              已有 12,800+ 位用户完成缘分测算
            </p>
          </div>
        </div>
      </section>

      {/* 第 2 屏：卖点区 */}
      <section className="px-5 pt-12 pb-14">
        <SectionHeading
          eyebrow="三大核心服务"
          title="缘之所起 · 测之有道"
          sub="从生辰八字出发，为每一段缘分提供专业解读"
        />
        <div className="mt-9 space-y-4">
          {FEATURES.map((f) => (
            <Card key={f.seal} className="flex items-start gap-4 p-4">
              <Seal char={f.seal} />
              <div className="flex-1">
                <h3 className="font-kai text-lg font-bold text-crimson">
                  {f.title}
                </h3>
                <p className="mt-1.5 text-sm leading-relaxed text-ink/65">
                  {f.desc}
                </p>
              </div>
            </Card>
          ))}
        </div>
        <div className="mt-8">
          <Link to="/calc" className="block">
            <Button
              size="lg"
              className="w-full rounded-full text-base font-bold"
            >
              免费测算，先看预览报告
            </Button>
          </Link>
        </div>
      </section>

      {/* 第 3 屏：信任背书 */}
      <section className="bg-gold-pale/40 px-5 pt-12 pb-14">
        <SectionHeading
          eyebrow="用户真实反馈"
          title="千人实测 · 好评如潮"
          sub="每一条评价，都是对缘分的真实见证"
        />
        <div className="mt-9 space-y-4">
          {TESTIMONIALS.map((t) => (
            <Card key={t.name} className="p-5">
              <div className="flex items-center justify-between">
                <StarRow />
                <span className="rounded-full bg-cinnabar/10 px-2 py-0.5 text-xs text-crimson">
                  {t.tag}
                </span>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-ink/80">
                “{t.text}”
              </p>
              <p className="mt-3 text-xs text-ink/45">— {t.name}</p>
            </Card>
          ))}
        </div>

        {/* 隐私承诺 */}
        <Card className="mt-6 flex items-center gap-4 border-cinnabar/20 p-5">
          <span
            aria-hidden="true"
            className="flex size-12 shrink-0 items-center justify-center rounded-full bg-cinnabar text-paper"
          >
            <svg
              viewBox="0 0 24 24"
              className="size-6"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="4" y="11" width="16" height="9" rx="2" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
          </span>
          <div>
            <h3 className="font-kai text-base font-bold text-crimson">
              隐私承诺 · 生辰信息加密存储
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-ink/60">
              你的生辰信息采用 AES-GCM 加密存储，仅用于本次测算，绝不泄露、不出售。
            </p>
          </div>
        </Card>

        {/* 数据背书 */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          {STATS.map((s) => (
            <div
              key={s.label}
              className="rounded-xl border border-gold/25 bg-white/80 py-4 text-center shadow-card"
            >
              <p className="font-kai text-lg font-bold text-cinnabar">
                {s.num}
              </p>
              <p className="mt-1 text-xs text-ink/55">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 第 4 屏：底部 CTA */}
      <section className="relative overflow-hidden bg-gradient-to-b from-crimson via-cinnabar to-crimson px-5 pt-12 pb-10 text-paper">
        <Xiangyun filled className="absolute -top-8 -right-16 w-44 text-gold-bright/20" />
        <Xiangyun className="absolute -bottom-12 -left-14 w-40 text-paper/12" />
        <div className="relative z-10 flex flex-col items-center text-center">
          <DoubleHappiness className="text-3xl" />
          <h2 className="mt-3 font-kai text-[1.9rem] leading-snug font-bold text-gold-grad">
            前世今缘 · 一试便知
          </h2>
          <p className="mt-3 max-w-[280px] text-sm leading-relaxed text-paper/80">
            填写双方生辰信息，立即生成专属合婚预览报告
          </p>
          <div className="mt-8 w-full max-w-[300px]">
            <Link to="/calc" className="block">
              <Button
                variant="gold"
                size="xl"
                className="w-full rounded-full border border-gold-bright/60 text-lg font-bold"
              >
                免费测算
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* 页脚 */}
      <footer className="pb-safe px-5 pt-8 pb-6 text-center">
        <Huiwen className="mx-auto w-40 text-gold/50" />
        <p className="mt-4 text-xs leading-relaxed text-ink/45">
          本页面内容由算法生成，仅供娱乐参考，不构成任何专业建议。
        </p>
        <p className="mt-2 text-xs text-ink/45">
          © 2026 振凡命理 · 快手磁力智投 H5
        </p>
      </footer>
    </main>
  )
}

export default LandingPage
