import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, type SelectOption } from '@/components/ui/select'
import { Huiwen } from '@/components/decor/Huiwen'
import PageHeader from '@/components/PageHeader'
import { createProfile, newIdempotencyKey, type CreateProfileResult } from '@/api/profiles'

const HOURS: SelectOption[] = [
  { value: '', label: '不详（选填）' },
  ...['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'].map(
    (h) => ({ value: h, label: `${h}时` }),
  ),
]

interface PersonForm {
  name: string
  birth: string
  birthHour: string
}

type PersonKey = 'A' | 'B'
type FieldErrors = Partial<Record<'nameA' | 'birthA' | 'nameB' | 'birthB', string>>

const EMPTY: PersonForm = { name: '', birth: '', birthHour: '' }

function validateName(name: string): string | undefined {
  const trimmed = name.trim()
  const len = [...trimmed].length
  if (!trimmed) return '请填写姓名'
  if (len < 2 || len > 20) return '姓名需为 2~20 个字'
  if (!/^[\u4e00-\u9fa5A-Za-z·\s-]+$/.test(trimmed))
    return '姓名仅支持中英文、间隔号'
  return undefined
}

function validateBirth(birth: string): string | undefined {
  if (!birth) return '请选择出生日期'
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birth)) return '出生日期格式不正确'
  const d = new Date(`${birth}T00:00:00`)
  if (Number.isNaN(d.getTime())) return '出生日期不合法'
  if (d.getFullYear() < 1900) return '请填写 1900 年以后的日期'
  const today = new Date()
  if (d.getTime() > today.getTime()) return '出生日期不能晚于今天'
  return undefined
}

function PersonSection({
  label,
  person,
  calendar,
  onChange,
  nameError,
  birthError,
}: {
  label: string
  person: PersonForm
  calendar: '公历' | '农历'
  onChange: (patch: Partial<PersonForm>) => void
  nameError?: string
  birthError?: string
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <span className="flex size-7 items-center justify-center rounded-md border-2 border-cinnabar/70 bg-cinnabar/5 font-kai text-sm font-bold text-cinnabar">
          {label}
        </span>
        <h2 className="font-serif text-lg font-bold text-ink">
          {label === '甲' ? '甲方' : '乙方'}生辰
        </h2>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <Label htmlFor={`name-${label}`}>
            姓名{calendar === '农历' ? '（可填农历名）' : ''}
          </Label>
          <Input
            id={`name-${label}`}
            value={person.name}
            maxLength={20}
            placeholder="请输入姓名（2~20 字）"
            aria-invalid={Boolean(nameError)}
            autoComplete="off"
            onChange={(e) => onChange({ name: e.target.value })}
          />
          {nameError ? (
            <p className="mt-1.5 text-xs text-cinnabar" role="alert">
              {nameError}
            </p>
          ) : null}
        </div>

        <div>
          <Label htmlFor={`birth-${label}`}>
            出生日期{calendar === '农历' ? '（农历）' : ''}
          </Label>
          <Input
            id={`birth-${label}`}
            type="date"
            value={person.birth}
            aria-invalid={Boolean(birthError)}
            onChange={(e) => onChange({ birth: e.target.value })}
          />
          {birthError ? (
            <p className="mt-1.5 text-xs text-cinnabar" role="alert">
              {birthError}
            </p>
          ) : null}
        </div>

        <div>
          <Label htmlFor={`hour-${label}`}>出生时辰</Label>
          <Select
            id={`hour-${label}`}
            options={HOURS}
            value={person.birthHour}
            aria-label={`${label === '甲' ? '甲方' : '乙方'}出生时辰`}
            onChange={(e) => onChange({ birthHour: e.target.value })}
          />
        </div>
      </div>
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
      strokeWidth="2"
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

function PreviewReport({ result }: { result: CreateProfileResult }) {
  const { profileId, previewReport } = result
  return (
    <section className="mt-10 scroll-mt-20" aria-label="预览报告">
      <div className="flex items-center gap-2">
        <Huiwen className="h-2 w-10 text-ink/30" />
        <h2 className="font-serif text-xl font-bold text-ink">测算结果</h2>
        <Huiwen className="h-2 w-10 text-ink/30" />
      </div>

      <Card className="mt-4 overflow-hidden border-ink/10">
        <CardContent className="p-0">
          <div className="border-b border-ink/10 bg-paper-deep/50 px-5 py-4">
            <p className="text-xs tracking-[0.3em] text-ink-faint">
              合婚测算 · 预览报告
            </p>
            <h3 className="mt-1 font-serif text-lg font-bold text-ink">
              {previewReport.title}
            </h3>
            <div className="mt-3 grid grid-cols-2 gap-2 font-serif text-xs text-ink-soft">
              <div className="flex items-center gap-1.5">
                契合指数：
                <span className="font-bold text-cinnabar">★★★★☆</span>
              </div>
              <div className="flex items-center gap-1.5">
                五行互补：<span className="font-bold text-cinnabar">4 / 5 项</span>
              </div>
              <div className="flex items-center gap-1.5">
                上等婚配：<span className="font-bold text-cinnabar">中等偏上</span>
              </div>
              <div className="flex items-center gap-1.5">
                正缘时机：<span className="font-bold text-cinnabar">今明两年</span>
              </div>
            </div>
          </div>

          {/* 掩码区域 */}
          <div className="relative px-5 py-6">
            <div aria-hidden="true" className="space-y-2.5 blur-sm select-none">
              {MASK_LINES.map((w, i) => (
                <div
                  key={i}
                  className={`h-2.5 rounded-sm ${i % 3 === 0 ? 'bg-ink/20' : 'bg-ink/8'}`}
                  style={{ width: `${w * 100}%` }}
                />
              ))}
            </div>

            <div className="absolute inset-0 flex flex-col items-center justify-center bg-paper/55 px-6 text-center backdrop-blur-[1px]">
              <span className="flex size-14 items-center justify-center rounded-full bg-ink text-paper-light shadow-ink">
                <LockIcon className="size-7" />
              </span>
              <p className="mt-3 font-serif text-base font-bold text-ink">
                {previewReport.lockedNote ?? '完整版需付费解锁'}
              </p>
              <p className="mt-1 font-serif text-xs leading-relaxed text-ink-soft">
                解锁后可查看完整合婚报告与
                <br />
                专属缘分建议
              </p>
            </div>
          </div>

          <p className="border-t border-ink/10 px-5 pt-3 pb-4 text-center font-serif text-xs text-ink-faint">
            报告编号：{profileId}
          </p>
        </CardContent>
      </Card>
    </section>
  )
}

function CalcPage() {
  const [personA, setPersonA] = useState<PersonForm>(EMPTY)
  const [personB, setPersonB] = useState<PersonForm>(EMPTY)
  const [isLunar, setIsLunar] = useState(false)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<CreateProfileResult | null>(null)
  const previewRef = useRef<HTMLDivElement>(null)

  const calendar = isLunar ? '农历' : '公历'

  const patch = (person: PersonKey, patchValue: Partial<PersonForm>) => {
    setErrors((prev) => ({ ...prev, [`name${person}`]: undefined, [`birth${person}`]: undefined }))
    if (person === 'A') setPersonA((p) => ({ ...p, ...patchValue }))
    else setPersonB((p) => ({ ...p, ...patchValue }))
  }

  const handleSubmit = async () => {
    const nextErrors: FieldErrors = {
      nameA: validateName(personA.name),
      birthA: validateBirth(personA.birth),
      nameB: validateName(personB.name),
      birthB: validateBirth(personB.birth),
    }
    const hasError = Object.values(nextErrors).some(Boolean)
    setErrors(nextErrors)
    if (hasError) {
      const first = (['nameA', 'birthA', 'nameB', 'birthB'] as const).find(
        (k) => nextErrors[k],
      )
      const fieldId = { nameA: 'name-甲', birthA: 'birth-甲', nameB: 'name-乙', birthB: 'birth-乙' } as const
      if (first) document.getElementById(fieldId[first])?.focus()
      return
    }

    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await createProfile(
        {
          nameA: personA.name.trim(),
          birthA: personA.birth,
          birthHourA: personA.birthHour || undefined,
          nameB: personB.name.trim(),
          birthB: personB.birth,
          birthHourB: personB.birthHour || undefined,
          isLunar,
        },
        newIdempotencyKey(),
      )
      setResult(res)
      requestAnimationFrame(() => previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
    } catch (err) {
      const msg =
        err instanceof Error && err.message ? err.message : '提交失败，请稍后重试'
      setSubmitError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen pb-28 text-ink">
      <PageHeader title="姻缘测算" backTo="/" />

      <div className="px-5">
        {/* 表单头部说明 */}
        <section className="pt-7 pb-5 text-center">
          <h1 className="font-serif text-[1.65rem] font-bold text-ink">
            生辰合婚 · 缘分测算
          </h1>
          <p className="mt-2 font-serif text-sm leading-relaxed text-ink-soft">
            填写双方生辰信息，免费生成专属合婚预览报告
          </p>

          {/* 公历/农历切换 */}
          <div className="mx-auto mt-5 flex w-fit rounded-full border border-ink/15 bg-paper-deep/60 p-1 shadow-card">
            {(['公历', '农历'] as const).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setIsLunar(c === '农历')}
                aria-pressed={calendar === c}
                className={`rounded-full px-5 py-1.5 font-serif text-sm transition-all ${
                  calendar === c
                    ? 'bg-gradient-to-r from-cinnabar to-cinnabar-dark font-medium text-paper-light shadow-cinnabar'
                    : 'text-ink-soft'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </section>

        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault()
            void handleSubmit()
          }}
          noValidate
        >
          <PersonSection
            label="甲"
            person={personA}
            calendar={calendar}
            onChange={(p) => patch('A', p)}
            nameError={errors.nameA}
            birthError={errors.birthA}
          />
          <PersonSection
            label="乙"
            person={personB}
            calendar={calendar}
            onChange={(p) => patch('B', p)}
            nameError={errors.nameB}
            birthError={errors.birthB}
          />

          {submitError ? (
            <p
              className="rounded-lg border border-cinnabar/25 bg-cinnabar/6 px-4 py-3 font-serif text-sm text-cinnabar"
              role="alert"
            >
              {submitError}
            </p>
          ) : null}

          <Button
            type="submit"
            size="lg"
            disabled={submitting}
            className="w-full rounded-full text-base font-bold"
          >
            {submitting ? (
              <>
                <svg
                  className="size-5 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-90"
                    fill="currentColor"
                    d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"
                  />
                </svg>
                正在测算…
              </>
            ) : (
              '开始免费测算'
            )}
          </Button>
        </form>

        <div ref={previewRef}>{result ? <PreviewReport result={result} /> : null}</div>
      </div>

      {/* 底部固定 CTA */}
      {result ? (
        <div className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-ink/10 bg-paper/95 backdrop-blur-md">
          <div className="flex items-center justify-between gap-4 px-5 py-3">
            <div>
              <p className="font-serif text-xs text-ink-faint">解锁完整版</p>
              <p className="font-serif text-xl font-bold text-cinnabar">
                ¥99
                <span className="ml-1 font-serif text-xs font-normal text-ink-faint">
                  一次解锁 · 永久查看
                </span>
              </p>
            </div>
            <Link to={`/order?profileId=${result.profileId}`} className="shrink-0">
              <Button
                variant="gold"
                size="lg"
                className="w-32 rounded-full text-base font-bold"
              >
                解锁完整版
              </Button>
            </Link>
          </div>
        </div>
      ) : null}
    </main>
  )
}

export default CalcPage
