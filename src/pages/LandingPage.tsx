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
          className="inline-block size-3.5 text-ochre"
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
      <span className="font-kai text-xs font-medium tracking-[0.45em] text-cinnabar">
        {eyebrow}
      </span>
      <h2 className="mt-2 font-serif text-[1.9rem] leading-snug font-bold text-ink">
        {title}
      </h2>
      <Huiwen className="mt-3 w-36 text-ink/30" />
      {sub ? (
        <p className="mt-3 max-w-[300px] font-serif text-sm leading-relaxed text-ink-soft">
          {sub}
        </p>
      ) : null}
    </header>
  )
}

/** 朱砂方印（服务图标） */
function Seal({ char }: { char: string }) {
  return (
    <span
      aria-hidden="true"
      className="flex size-11 shrink-0 items-center justify-center rounded-lg border-2 border-cinnabar/70 bg-cinnabar/5 font-kai text-lg font-bold text-cinnabar"
    >
      {char}
    </span>
  )
}

/** 墨色远山剪影（淡墨分层） */
function Mountains({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 1440 320"
      preserveAspectRatio="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M0 218 C 220 140, 380 58, 580 108 C 770 154, 880 88, 1100 148 C 1260 190, 1360 158, 1440 198 L 1440 320 L 0 320 Z"
        fill="currentColor"
        opacity="0.5"
      />
      <path
        d="M0 262 C 200 200, 340 252, 530 190 C 720 128, 880 212, 1050 160 C 1230 108, 1350 202, 1440 168 L 1440 320 L 0 320 Z"
        fill="currentColor"
        opacity="0.28"
      />
      <path
        d="M0 302 C 170 258, 310 300, 470 258 C 650 210, 790 292, 970 248 C 1170 202, 1310 282, 1440 238 L 1440 320 L 0 320 Z"
        fill="currentColor"
        opacity="0.14"
      />
    </svg>
  )
}

/** 阴阳双鱼（墨 / 朱砂） */
function Taiji({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      aria-hidden="true"
    >
      <circle
        cx="50"
        cy="50"
        r="46"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        opacity="0.8"
      />
      <path
        d="M50 4 A46 46 0 0 1 50 96 A23 23 0 0 1 50 50 A23 23 0 0 0 50 4 Z"
        fill="currentColor"
        opacity="0.85"
      />
      <path
        d="M50 4 A46 46 0 0 0 50 96 A23 23 0 0 0 50 50 A23 23 0 0 1 50 4 Z"
        fill="var(--color-cinnabar)"
        opacity="0.85"
      />
      <circle cx="50" cy="27" r="7" fill="var(--color-cinnabar)" />
      <circle cx="50" cy="73" r="7" fill="currentColor" opacity="0.85" />
    </svg>
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
    <main className="min-h-screen text-ink">
      {/* 第 1 屏：全屏 Hero（水墨留白 + 墨色远山） */}
      <section className="relative flex min-h-[100dvh] flex-col overflow-hidden">
        {/* 墨晕微光 */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0">
          <div className="absolute -top-24 left-1/2 h-64 w-[30rem] max-w-full -translate-x-1/2 rounded-full bg-ink/4 blur-[90px]" />
          <div className="absolute top-1/3 -right-20 size-56 rounded-full bg-cinnabar/6 blur-[80px]" />
        </div>
        {/* 装饰祥云（淡墨） */}
        <Xiangyun className="absolute top-1/5 -left-12 w-36 -rotate-6 text-ink/10" />
        <Xiangyun filled className="absolute top-1/2 -right-14 w-40 text-ink/6" />

        {/* 右上朱砂印章 */}
        <div className="pt-safe absolute top-3 right-4 z-10">
          <span
            aria-hidden="true"
            className="flex size-11 items-center justify-center rounded-md border-2 border-cinnabar/80 bg-cinnabar/5 font-kai text-lg font-bold text-cinnabar"
          >
            振凡
          </span>
        </div>

        {/* 中央内容 */}
        <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-7 pt-16 pb-10 text-center">
          <div className="animate-fade-up">
            <DoubleHappiness className="text-5xl text-cinnabar/80" />
            <h1 className="mt-4 font-kai text-[2.7rem] leading-[1.22] font-bold text-ink">
              天生一对
              <span className="mt-1 block font-serif text-[1.6rem] font-medium tracking-[0.35em] text-ink-soft">
                缘定三生
              </span>
            </h1>

            <div className="mt-6 flex items-center justify-center gap-2.5 text-ink/35">
              <Huiwen className="h-2 w-12" />
              <StarSeal className="size-2 text-cinnabar/70" />
              <Huiwen className="h-2 w-12" />
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 font-serif text-sm text-ink-soft">
              {['免费出报告', '无需注册', '30 秒出结果'].map((t) => (
                <span key={t} className="flex items-center gap-1.5">
                  <StarSeal className="size-1.5 text-cinnabar/70" />
                  {t}
                </span>
              ))}
            </div>

            <div className="mt-10 w-full max-w-[300px]">
              <Link to="/calc" className="block">
                <Button
                  variant="gold"
                  size="xl"
                  className="w-full rounded-full text-lg font-bold"
                >
                  免费测算
                </Button>
              </Link>
              <p className="mt-3 text-center font-serif text-xs text-ink-faint">
                已有 12,800+ 位用户完成缘分测算
              </p>
            </div>
          </div>
        </div>

        {/* 墨色远山 */}
        <Mountains className="pointer-events-none absolute inset-x-0 bottom-0 h-40 w-full text-ink" />

        {/* 下滑提示 */}
        <div className="relative z-10 mb-2 flex flex-col items-center gap-1.5 pb-2 text-ink-faint">
          <span className="font-serif text-[10px] tracking-[0.4em]">下 滑 探 缘</span>
          <span className="block h-6 w-px animate-float bg-ink/30" aria-hidden="true" />
        </div>
      </section>

      {/* 第 2 屏：引言带（深纸底） */}
      <section className="relative overflow-hidden bg-paper-deep/60 px-8 py-16 text-center">
        <Xiangyun className="absolute -top-6 -right-10 w-32 text-ink/8" />
        <p className="mx-auto max-w-[280px] font-serif text-[1.05rem] leading-[2.1] text-ink/80">
          缘之所起，命之所属。
          <br />
          生辰八字之间，
          <br />
          藏着两个人的前世今缘。
        </p>
        <div className="mt-6 flex items-center justify-center gap-2 text-ink-faint">
          <span className="h-px w-8 bg-ink/25" />
          <span className="font-kai text-sm tracking-[0.5em] text-cinnabar">缘</span>
          <span className="h-px w-8 bg-ink/25" />
        </div>
      </section>

      {/* 第 3 屏：三大服务（白纸底） */}
      <section className="px-5 py-16">
        <SectionHeading
          eyebrow="三大核心服务"
          title="缘之所起 · 测之有道"
          sub="从生辰八字出发，为每一段缘分提供专业解读"
        />
        <div className="mt-10 space-y-4">
          {FEATURES.map((f) => (
            <Card key={f.seal} className="flex items-start gap-4 p-4">
              <Seal char={f.seal} />
              <div className="flex-1">
                <h3 className="font-serif text-lg font-bold text-ink">
                  {f.title}
                </h3>
                <p className="mt-1.5 font-serif text-sm leading-relaxed text-ink-soft">
                  {f.desc}
                </p>
              </div>
            </Card>
          ))}
        </div>
        <div className="mt-9">
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

      {/* 第 4 屏：阴阳沉浸带（深纸底） */}
      <section className="relative overflow-hidden bg-paper-deep/60 px-8 py-16">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cinnabar/4 blur-[70px]"
        />
        <div className="relative flex flex-col items-center text-center">
          <Taiji className="size-24 text-ink" />
          <p className="mt-8 font-kai text-xl tracking-[0.3em] text-ink">
            阴阳和合 · 五行相生
          </p>
          <p className="mt-3 max-w-[260px] font-serif text-sm leading-relaxed text-ink-soft">
            一阴一阳之谓道。八字合婚，观其相生相克，求其和合圆满。
          </p>
        </div>
      </section>

      {/* 第 5 屏：信任背书（白纸底） */}
      <section className="px-5 py-16">
        <SectionHeading
          eyebrow="用户真实反馈"
          title="千人实测 · 好评如潮"
          sub="每一条评价，都是对缘分的真实见证"
        />
        <div className="mt-10 space-y-4">
          {TESTIMONIALS.map((t) => (
            <Card key={t.name} className="p-5">
              <div className="flex items-center justify-between">
                <StarRow />
                <span className="rounded-full bg-cinnabar/10 px-2 py-0.5 text-xs text-cinnabar">
                  {t.tag}
                </span>
              </div>
              <p className="mt-3 font-serif text-sm leading-relaxed text-ink/85">
                “{t.text}”
              </p>
              <p className="mt-3 text-xs text-ink-faint">— {t.name}</p>
            </Card>
          ))}
        </div>

        {/* 隐私承诺 */}
        <Card className="mt-6 flex items-center gap-4 border-ink/10 p-5">
          <span
            aria-hidden="true"
            className="flex size-11 shrink-0 items-center justify-center rounded-lg border border-ink/25 bg-paper-deep/60 text-ink-soft"
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
            <h3 className="font-serif text-base font-bold text-ink">
              隐私承诺 · 生辰信息加密存储
            </h3>
            <p className="mt-1 font-serif text-sm leading-relaxed text-ink-soft">
              你的生辰信息采用 AES-GCM 加密存储，仅用于本次测算，绝不泄露、不出售。
            </p>
          </div>
        </Card>

        {/* 数据背书 */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          {STATS.map((s) => (
            <div
              key={s.label}
              className="paper-card rounded-xl py-5 text-center"
            >
              <p className="font-serif text-lg font-bold text-ink">{s.num}</p>
              <p className="mt-1 font-serif text-xs text-ink-soft">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 第 6 屏：朱砂 CTA（落款式） */}
      <section className="relative overflow-hidden px-6 pt-14 pb-12">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-cinnabar to-cinnabar-dark px-6 pt-12 pb-10 text-center shadow-cinnabar">
          <Xiangyun className="absolute -top-8 -right-10 w-36 rotate-12 text-paper-light/15" />
          <Xiangyun filled className="absolute -bottom-10 -left-8 w-32 text-paper-light/10" />
          <div className="relative z-10 flex flex-col items-center text-center">
            <DoubleHappiness className="text-4xl text-paper-light/90" />
            <h2 className="mt-4 font-kai text-[1.8rem] leading-snug font-bold text-paper-light">
              前世今缘 · 一试便知
            </h2>
            <p className="mt-3 max-w-[280px] font-serif text-sm leading-relaxed text-paper-light/85">
              填写双方生辰信息，立即生成专属合婚预览报告
            </p>
            <div className="mt-8 w-full max-w-[300px]">
              <Link to="/calc" className="block">
                <Button
                  size="xl"
                  className="w-full rounded-full border border-paper-light/50 bg-paper-light text-cinnabar text-lg font-bold shadow-ink hover:bg-paper"
                >
                  免费测算
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 页脚 */}
      <footer className="pb-safe px-5 pt-4 pb-8 text-center">
        <Huiwen className="mx-auto w-40 text-ink/25" />
        <p className="mt-4 font-serif text-xs leading-relaxed text-ink-faint">
          本页面内容由算法生成，仅供娱乐参考，不构成任何专业建议。
        </p>
        <p className="mt-2 font-serif text-xs text-ink-faint">
          © 2026 振凡命理 · 快手磁力智投 H5
        </p>
      </footer>
    </main>
  )
}

export default LandingPage
