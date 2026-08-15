import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createProfile, newIdempotencyKey } from '@/api/profiles'

const HOURS = [
  { value: '子', label: '子时 (23:00 - 00:59)' },
  { value: '丑', label: '丑时 (01:00 - 02:59)' },
  { value: '寅', label: '寅时 (03:00 - 04:59)' },
  { value: '卯', label: '卯时 (05:00 - 06:59)' },
  { value: '辰', label: '辰时 (07:00 - 08:59)' },
  { value: '巳', label: '巳时 (09:00 - 10:59)' },
  { value: '午', label: '午时 (11:00 - 12:59)' },
  { value: '未', label: '未时 (13:00 - 14:59)' },
  { value: '申', label: '申时 (15:00 - 16:59)' },
  { value: '酉', label: '酉时 (17:00 - 18:59)' },
  { value: '戌', label: '戌时 (19:00 - 20:59)' },
  { value: '亥', label: '亥时 (21:00 - 22:59)' },
  { value: '吉时', label: '时辰不详 (系统推算)' },
]

const FOCUS_TAGS = ['八字五行匹配', '正缘结婚年限', '婚后财运旺衰', '性格相克化解', '子女缘分推演']
const DEFAULT_FOCUS = ['八字五行匹配', '正缘结婚年限', '婚后财运旺衰']

const LOADING_STEPS = [
  '排盘天干地支四柱与纳音五行...',
  '推演二人八字喜用相生相克...',
  '计算正缘结婚转折年份与婚后财运...',
  '生成月老密签与化解锦囊...',
]

/** 推演超时阈值：30s 未完成则展示重试容器 */
const SUBMIT_TIMEOUT_MS = 30000

/** 预览结果持久化：提交成功后跳 /order，返回本页时仍展示预览卡 */
const RESULT_KEY = 'calc-last-result'

interface PersonForm {
  name: string
  birth: string
  birthHour: string
}

interface StoredResult {
  profileId: string
  title: string
  lockedNote?: string
}

type PersonKey = 'A' | 'B'
type FieldErrors = Partial<Record<'nameA' | 'birthA' | 'nameB' | 'birthB', string>>

const EMPTY: PersonForm = { name: '', birth: '', birthHour: '' }

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

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

/* ---------------- 全屏推演遮罩（03-loading） ---------------- */

function CalcLoading({
  maleName,
  femaleName,
  progress,
  timedOut,
  onRetry,
}: {
  maleName: string
  femaleName: string
  progress: number
  timedOut: boolean
  onRetry: () => void
}) {
  const doneCount = progress >= 100 ? 4 : Math.floor(progress / 25)

  return (
    <div
      className="fx-paper fx-cloud fade-in fixed inset-0 z-50 flex flex-col items-center overflow-y-auto bg-[radial-gradient(circle_at_50%_20%,#8a1a1a_0%,#5a0f0f_55%,#3a0a0a_100%)] px-5 py-8 text-center"
      role="status"
      aria-live="polite"
    >
      <div>
        <h2 className="mb-1.5 font-kai text-[22px] tracking-[0.08em] text-gold-light">
          天机交感 · 姻缘推演
        </h2>
        <p className="text-[13px] text-muted">
          正在排盘计算双方八字五行生克与宿世姻缘
        </p>
      </div>

      {/* 双人命盘两极 + 红线 */}
      <div className="relative my-5 flex w-full items-center justify-around">
        <div className="relative z-10 flex flex-col items-center gap-1.5">
          <span className="grid size-[58px] animate-pulse-glow-slow place-items-center rounded-full border-2 border-gold bg-[radial-gradient(circle,#4a0e0e_0%,#2a0808_100%)] font-kai text-lg text-gold-light shadow-[0_0_16px_rgba(226,180,95,0.4)]">
            乾
          </span>
          <span className="max-w-[120px] truncate text-[13px] font-medium text-fg">
            {maleName}
          </span>
        </div>

        <div
          aria-hidden="true"
          className="absolute top-[29px] right-[20%] left-[20%] z-0 h-0.5 bg-gradient-to-r from-gold via-gold-light to-gold shadow-[0_0_10px_var(--color-gold)]"
        />
        <span className="absolute top-1/2 left-1/2 z-10 grid size-6 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-gold-light bg-gold text-[11px] text-[#591010] shadow-[0_0_12px_var(--color-gold)]">
          缘
        </span>

        <div className="relative z-10 flex flex-col items-center gap-1.5">
          <span className="grid size-[58px] animate-pulse-glow-slow place-items-center rounded-full border-2 border-gold bg-[radial-gradient(circle,#4a0e0e_0%,#2a0808_100%)] font-kai text-lg text-gold-light shadow-[0_0_16px_rgba(226,180,95,0.4)]">
            坤
          </span>
          <span className="max-w-[120px] truncate text-[13px] font-medium text-fg">
            {femaleName}
          </span>
        </div>
      </div>

      {/* 太极罗盘 */}
      <div className="relative mx-auto my-2.5 flex size-[180px] items-center justify-center">
        <div
          aria-hidden="true"
          className="absolute size-[180px] animate-compass-fast rounded-full border-2 border-dashed border-border-gold"
        />
        <div
          aria-hidden="true"
          className="absolute size-[130px] animate-reverse-fast rounded-full border-[1.5px] border-gold shadow-[0_0_15px_rgba(226,180,95,0.4)]"
        />
        <div
          className="relative size-[70px] animate-taiji rounded-full border-2 border-gold shadow-[0_0_20px_rgba(226,180,95,0.5)]"
          style={{ background: 'conic-gradient(#f8ebdb 0deg 180deg, #100806 180deg 360deg)' }}
        >
          <span
            aria-hidden="true"
            className="absolute top-0 left-[25%] size-[35px] rounded-full bg-[#f8ebdb] shadow-[inset_0_0_0_6px_#100806]"
          />
          <span
            aria-hidden="true"
            className="absolute bottom-0 left-[25%] size-[35px] rounded-full bg-[#100806] shadow-[inset_0_0_0_6px_#f8ebdb]"
          />
        </div>
      </div>

      {/* 实时演算状态日志 */}
      <div className="w-full rounded-[16px] border border-border-gold bg-[#3a0a0a]/70 p-4 text-left">
        {LOADING_STEPS.map((text, i) => {
          const done = i < doneCount
          const active = !done && i === doneCount
          return (
            <div
              key={text}
              className={`mb-2 flex items-center gap-2.5 text-[13px] transition-colors duration-300 ${
                done
                  ? 'text-jade-light'
                  : active
                    ? 'font-medium text-gold-light'
                    : 'text-muted'
              }`}
            >
              <span
                aria-hidden="true"
                className="grid size-4 shrink-0 place-items-center rounded-full border text-[10px]"
                style={{ borderColor: 'currentColor' }}
              >
                {done ? '✓' : i + 1}
              </span>
              <span>{text}</span>
            </div>
          )
        })}

        <div className="mt-2.5">
          <div
            className="h-1.5 overflow-hidden rounded-full border border-border bg-[#5a1414]/60"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
          >
            <div
              className="h-full rounded-full bg-gradient-to-r from-gold-dark via-gold to-gold-light shadow-[0_0_10px_var(--color-gold)] transition-[width] duration-100"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-1.5 flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted">
              网络安全连接中 · 请勿关闭页面
            </span>
            <span className="font-mono text-xs text-gold" aria-live="polite">
              {progress}%
            </span>
          </div>
          {timedOut ? (
            <div className="mt-3 rounded-[10px] border border-red/25 bg-red/10 px-3 py-3 text-center">
              <p className="text-xs leading-relaxed text-red-light">
                推演耗时稍长，已为您保留排盘数据
              </p>
              <div className="mt-2.5 flex justify-center">
                <button
                  type="button"
                  onClick={onRetry}
                  className="btn-guofeng-ghost !min-h-[36px] !w-auto !px-5 !text-[13px]"
                >
                  重新发起推演
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

/* ---------------- 个人信息卡片（乾造 / 坤造） ---------------- */

function PersonSection({
  gender,
  name,
  birth,
  birthHour,
  calendar,
  onToggleCalendar,
  onChange,
  nameError,
  birthError,
}: {
  gender: 'male' | 'female'
  name: string
  birth: string
  birthHour: string
  calendar: '公历' | '农历'
  onToggleCalendar: (cal: '公历' | '农历') => void
  onChange: (patch: Partial<PersonForm>) => void
  nameError?: string
  birthError?: string
}) {
  const isMale = gender === 'male'
  return (
    <section className="rounded-[16px] border border-border-gold bg-surface-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div
          className={`font-kai text-[15px] font-bold ${
            isMale ? 'text-blue' : 'text-pink'
          }`}
        >
          {isMale ? '乾造（男方信息）' : '坤造（女方信息）'}
        </div>
        <div
          className="flex rounded-full border border-border bg-[#3a0a0a]/55 p-0.5 text-[11px]"
          role="group"
          aria-label="历法切换"
        >
          {(['公历', '农历'] as const).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => onToggleCalendar(c)}
              aria-pressed={calendar === c}
              className={`cal-opt ${calendar === c ? 'active' : ''}`}
            >
              {c === '公历' ? '公历(阳历)' : '农历(阴历)'}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <label
            htmlFor={`${gender}-name`}
            className="mb-1 block text-xs text-fg-secondary"
          >
            {isMale ? '男方姓名/昵称' : '女方姓名/昵称'}
            <span className="text-red-light" aria-hidden="true"> *</span>
          </label>
          <input
            id={`${gender}-name`}
            type="text"
            className={`input-guofeng ${nameError ? 'input-error' : ''}`}
            value={name}
            maxLength={20}
            placeholder={`请输入${isMale ? '男方' : '女方'}姓名`}
            aria-invalid={Boolean(nameError)}
            aria-required="true"
            required
            autoComplete="off"
            onChange={(e) => onChange({ name: e.target.value })}
          />
          {nameError ? (
            <p className="field-error-msg" role="alert">
              {nameError}
            </p>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label
              htmlFor={`${gender}-date`}
              className="mb-1 block text-xs text-fg-secondary"
            >
              出生日期{calendar === '农历' ? '（农历）' : ''}
              <span className="text-red-light" aria-hidden="true"> *</span>
            </label>
            <input
              id={`${gender}-date`}
              type="date"
              className={`input-guofeng ${birthError ? 'input-error' : ''}`}
              value={birth}
              aria-invalid={Boolean(birthError)}
              aria-required="true"
              required
              onChange={(e) => onChange({ birth: e.target.value })}
            />
            {birthError ? (
              <p className="field-error-msg" role="alert">
                {birthError}
              </p>
            ) : null}
          </div>
          <div>
            <label
              htmlFor={`${gender}-hour`}
              className="mb-1 block text-xs text-fg-secondary"
            >
              出生时辰
            </label>
            <select
              id={`${gender}-hour`}
              className="input-guofeng"
              value={birthHour}
              onChange={(e) => onChange({ birthHour: e.target.value })}
            >
              {HOURS.map((h) => (
                <option key={h.value || 'unknown'} value={h.value}>
                  {h.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ---------------- 预览报告（返回本页时展示） ---------------- */

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

function PreviewReport({ result }: { result: StoredResult }) {
  return (
    <section className="mt-4" aria-label="预览报告">
      <div className="overflow-hidden rounded-[16px] border border-border-gold bg-surface-card shadow-card">
        <div className="border-b border-border bg-gradient-to-b from-[#5a0f0f]/60 to-transparent px-5 py-4">
          <p className="text-xs tracking-[0.3em] text-muted">合婚测算 · 预览报告</p>
          <h3 className="mt-1 font-kai text-lg font-bold text-gold-light">
            {result.title}
          </h3>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-fg-secondary">
            <div className="flex items-center gap-1.5">
              契合指数：<span className="font-bold text-gold">★★★★☆</span>
            </div>
            <div className="flex items-center gap-1.5">
              五行互补：<span className="font-bold text-gold">4 / 5 项</span>
            </div>
            <div className="flex items-center gap-1.5">
              上等婚配：<span className="font-bold text-gold">中等偏上</span>
            </div>
            <div className="flex items-center gap-1.5">
              正缘时机：<span className="font-bold text-gold">今明两年</span>
            </div>
          </div>
        </div>

        {/* 掩码区域 */}
        <div className="relative px-5 py-6">
          <div aria-hidden="true" className="space-y-2.5 blur-sm select-none">
            {MASK_LINES.map((w, i) => (
              <div
                key={i}
                className={`h-2.5 rounded-sm ${
                  i % 3 === 0 ? 'bg-gold/20' : 'bg-gold/10'
                }`}
                style={{ width: `${w * 100}%` }}
              />
            ))}
          </div>

          <div className="absolute inset-0 flex flex-col items-center justify-center bg-bg/60 px-6 text-center backdrop-blur-[1px]">
            <span className="flex size-14 items-center justify-center rounded-full bg-gradient-to-b from-gold to-gold-dark text-[#591010] shadow-[0_0_20px_rgba(226,180,95,0.6)]">
              <LockIcon className="size-7" />
            </span>
            <p className="mt-3 font-kai text-base font-bold text-gold-light">
              {result.lockedNote ?? '完整版需付费解锁'}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-fg-secondary">
              解锁后可查看完整合婚报告与
              <br />
              专属缘分建议
            </p>
          </div>
        </div>

        <p className="border-t border-border px-5 pt-3 pb-4 text-center text-xs text-muted">
          报告编号：{result.profileId}
        </p>
      </div>
    </section>
  )
}

/* ---------------- 页面 ---------------- */

function CalcPage() {
  const navigate = useNavigate()
  const [personA, setPersonA] = useState<PersonForm>(EMPTY)
  const [personB, setPersonB] = useState<PersonForm>(EMPTY)
  const [isLunar, setIsLunar] = useState(false)
  const [focusTags, setFocusTags] = useState<string[]>(DEFAULT_FOCUS)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<StoredResult | null>(null)
  const [showLoading, setShowLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [timedOut, setTimedOut] = useState(false)
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const calendar = isLunar ? '农历' : '公历'

  /* 返回本页时恢复上次测算的预览卡 */
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(RESULT_KEY)
      if (raw) {
        const stored = JSON.parse(raw) as StoredResult
        if (stored?.profileId && stored?.title) setResult(stored)
      }
    } catch {
      /* 忽略损坏数据 */
    }
  }, [])

  /* 卸载时清理进度定时器、超时定时器与进行中的请求 */
  useEffect(
    () => () => {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      if (abortRef.current) abortRef.current.abort()
    },
    [],
  )

  const patch = (person: PersonKey, patchValue: Partial<PersonForm>) => {
    setErrors((prev) => ({
      ...prev,
      [`name${person}`]: undefined,
      [`birth${person}`]: undefined,
    }))
    if (person === 'A') setPersonA((p) => ({ ...p, ...patchValue }))
    else setPersonB((p) => ({ ...p, ...patchValue }))
  }

  const toggleFocus = (tag: string) => {
    setFocusTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    )
  }

  const startSubmit = async () => {
    setSubmitError(null)
    setShowLoading(true)
    setProgress(0)
    setTimedOut(false)

    /* 中止上一次挂起的请求，避免并发提交 */
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    if (progressTimerRef.current) clearInterval(progressTimerRef.current)
    const timer = setInterval(() => {
      setProgress((p) => Math.min(p + 2, 100))
    }, 50)
    progressTimerRef.current = timer

    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => {
      setTimedOut(true)
    }, SUBMIT_TIMEOUT_MS)

    try {
      const [res] = await Promise.all([
        createProfile(
          {
            nameA: personA.name.trim(),
            birthA: personA.birth,
            birthHourA: personA.birthHour || undefined,
            nameB: personB.name.trim(),
            birthB: personB.birth,
            birthHourB: personB.birthHour || undefined,
            isLunar,
            focusTags,
          },
          newIdempotencyKey(),
          { signal: controller.signal },
        ),
        delay(2600),
      ])
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      setTimedOut(false)
      setProgress(100)
      const stored: StoredResult = {
        profileId: res.profileId,
        title: res.previewReport.title,
        lockedNote: res.previewReport.lockedNote,
      }
      sessionStorage.setItem(RESULT_KEY, JSON.stringify(stored))
      setResult(stored)
      await delay(500)
      navigate(`/order?profileId=${res.profileId}`)
    } catch (err) {
      /* 被「重新发起推演」中止的旧请求：静默忽略，新请求已接管 */
      if ((err as { code?: string } | null)?.code === 'ERR_CANCELED') return
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      setTimedOut(false)
      setShowLoading(false)
      setSubmitError(
        err instanceof Error && err.message ? err.message : '提交失败，请稍后重试',
      )
    }
  }

  const handleSubmit = async () => {
    if (showLoading) return
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
      const fieldId = {
        nameA: 'male-name',
        birthA: 'male-date',
        nameB: 'female-name',
        birthB: 'female-date',
      } as const
      if (first) document.getElementById(fieldId[first])?.focus()
      return
    }

    await startSubmit()
  }

  const handleRetry = () => {
    void startSubmit()
  }

  return (
    <main className={`fx-paper fx-cloud fade-in min-h-screen ${result ? 'pb-28' : 'pb-6'}`}>
      {/* 顶部导航 */}
      <div className="border-b border-border px-5 pt-3 pb-2">
        <div className="flex items-center justify-between">
          <Link
            to="/"
            aria-label="返回首页"
            className="flex items-center gap-1 text-[13px] text-muted transition-colors hover:text-gold"
          >
            <svg
              viewBox="0 0 24 24"
              className="size-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M15 18l-6-6 6-6" />
            </svg>
            <span>返回</span>
          </Link>
          <h2 className="font-kai text-[17px] text-gold-light">生辰八字排盘</h2>
          <span className="seal-mark">八字合婚</span>
        </div>
      </div>

      <form
        className="flex flex-col gap-4 px-5 pt-4"
        onSubmit={(e) => {
          e.preventDefault()
          void handleSubmit()
        }}
        noValidate
      >
        <PersonSection
          gender="male"
          name={personA.name}
          birth={personA.birth}
          birthHour={personA.birthHour}
          calendar={calendar}
          onToggleCalendar={(c) => setIsLunar(c === '农历')}
          onChange={(p) => patch('A', p)}
          nameError={errors.nameA}
          birthError={errors.birthA}
        />

        <PersonSection
          gender="female"
          name={personB.name}
          birth={personB.birth}
          birthHour={personB.birthHour}
          calendar={calendar}
          onToggleCalendar={(c) => setIsLunar(c === '农历')}
          onChange={(p) => patch('B', p)}
          nameError={errors.nameB}
          birthError={errors.birthB}
        />

        {/* 核心关注维度 */}
        <section className="rounded-[16px] border border-border-gold bg-surface-card p-4">
          <p className="mb-2 text-xs font-medium text-gold-light">
            核心关注维度 (可多选)
          </p>
          <div className="flex flex-wrap gap-2">
            {FOCUS_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleFocus(tag)}
                aria-pressed={focusTags.includes(tag)}
                className={`tag-chip ${focusTags.includes(tag) ? 'active' : ''}`}
              >
                {tag}
              </button>
            ))}
          </div>
        </section>

        {submitError ? (
          <p
            className="rounded-lg border border-red/25 bg-red/10 px-4 py-3 text-sm text-red-light"
            role="alert"
          >
            {submitError}
          </p>
        ) : null}

        <button type="submit" className="btn-guofeng-primary" disabled={showLoading}>
          <span>天地交泰 · 开启命盘演练</span>
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            aria-hidden="true"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </form>

      {result ? <div className="px-5">
        <PreviewReport result={result} />
      </div> : null}

      {/* 底部固定解锁栏（返回本页且有预览结果时） */}
      {result ? (
        <div className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-border-gold bg-[#2e0808]/96 backdrop-blur-md">
          <div className="flex items-center justify-between gap-4 px-5 py-3">
            <div>
              <p className="text-xs text-muted">解锁完整版</p>
              <p className="font-kai text-xl font-bold text-gold">
                ¥99
                <span className="ml-1 text-xs font-normal text-muted">
                  一次解锁 · 永久查看
                </span>
              </p>
            </div>
            <div className="w-32 shrink-0">
              <Link to={`/order?profileId=${result.profileId}`} className="block">
                <button type="button" className="btn-guofeng-primary !min-h-[46px] !text-[15px]">
                  解锁完整版
                </button>
              </Link>
            </div>
          </div>
        </div>
      ) : null}

      {/* 全屏推演遮罩 */}
      {showLoading ? (
        <CalcLoading
          maleName={personA.name.trim() || '男方'}
          femaleName={personB.name.trim() || '女方'}
          progress={progress}
          timedOut={timedOut}
          onRetry={handleRetry}
        />
      ) : null}
    </main>
  )
}

export default CalcPage
