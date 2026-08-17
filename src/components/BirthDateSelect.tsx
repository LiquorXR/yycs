import { useEffect, useMemo, useState } from 'react'
import { Lunar, LunarMonth, LunarYear, Solar } from 'lunar-typescript'

interface BirthDateSelectProps {
  birth: string
  calendar: '公历' | '农历'
  error?: string
  onChange: (birth: string) => void
}

const MIN_YEAR = 1900
const MAX_YEAR = new Date().getFullYear()

const YEARS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, i) => {
  const y = MIN_YEAR + i
  return { value: String(y), label: `${y}年` }
})

function formatDate(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

/** 公历某月天数（month 为 1~12，Date 自动处理闰年 2 月） */
function daysInGregorianMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

/**
 * 出生日期三级下拉（年/月/日），支持公历与农历（含闰月）。
 * 农历模式下选中的农历日期会换算为公历 YYYY-MM-DD 通过 onChange 上抛，
 * 由父组件存入 birth（后端以公历排盘）。
 */
export default function BirthDateSelect({
  birth,
  calendar,
  error,
  onChange,
}: BirthDateSelectProps) {
  const [year, setYear] = useState('')
  const [month, setMonth] = useState('')
  const [day, setDay] = useState('')

  /* 用户操作驱动的 birth 变化由内部状态直接接管，仅在历法切换时按 birth 重算回显 */
  useEffect(() => {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birth)
    if (!m) {
      setYear('')
      setMonth('')
      setDay('')
      return
    }
    const y = Number(m[1])
    const mo = Number(m[2])
    const d = Number(m[3])
    if (calendar === '农历') {
      const lunar = Solar.fromYmd(y, mo, d).getLunar()
      setYear(String(lunar.getYear()))
      setMonth(String(lunar.getMonth()))
      setDay(String(lunar.getDay()))
    } else {
      setYear(String(y))
      setMonth(String(mo))
      setDay(String(d))
    }
  }, [birth, calendar])

  const monthOptions = useMemo(() => {
    if (calendar === '公历') {
      return Array.from({ length: 12 }, (_, i) => ({
        value: String(i + 1),
        label: `${i + 1}月`,
      }))
    }
    if (!year) return []
    const ly = Number(year)
    const leap = LunarYear.fromYear(ly).getLeapMonth()
    const opts: { value: string; label: string }[] = []
    for (let m = 1; m <= 12; m++) {
      const name = Lunar.fromYmd(ly, m, 1).getMonthInChinese()
      opts.push({ value: String(m), label: `${name}月` })
      if (m === leap) opts.push({ value: String(-m), label: `闰${name}月` })
    }
    return opts
  }, [calendar, year])

  const dayOptions = useMemo(() => {
    if (!year || !month) return []
    const lm = LunarMonth.fromYm(Number(year), Number(month))
    const count =
      calendar === '公历'
        ? daysInGregorianMonth(Number(year), Number(month))
        : lm
          ? lm.getDayCount()
          : 0
    return Array.from({ length: count }, (_, i) => ({
      value: String(i + 1),
      label: `${i + 1}日`,
    }))
  }, [calendar, year, month])

  const emit = (y: string, m: string, d: string) => {
    if (!y || !m || !d) {
      onChange('')
      return
    }
    const value =
      calendar === '农历'
        ? Lunar.fromYmd(Number(y), Number(m), Number(d)).getSolar().toYmd()
        : formatDate(Number(y), Number(m), Number(d))
    onChange(value)
  }

  const handleYear = (v: string) => {
    setYear(v)
    setMonth('')
    setDay('')
    emit(v, '', '')
  }

  const handleMonth = (v: string) => {
    setMonth(v)
    setDay('')
    emit(year, v, '')
  }

  const handleDay = (v: string) => {
    setDay(v)
    emit(year, month, v)
  }

  return (
    <div
      role="group"
      aria-labelledby="person-date-label"
      className="grid grid-cols-3 gap-2"
    >
      <select
        id="person-date"
        className={`input-guofeng ${error ? 'input-error' : ''}`}
        value={year}
        aria-invalid={Boolean(error)}
        aria-required="true"
        onChange={(e) => handleYear(e.target.value)}
      >
        <option value="">年</option>
        {YEARS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <select
        className={`input-guofeng ${error ? 'input-error' : ''}`}
        value={month}
        aria-invalid={Boolean(error)}
        aria-required="true"
        onChange={(e) => handleMonth(e.target.value)}
      >
        <option value="">月</option>
        {monthOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <select
        className={`input-guofeng ${error ? 'input-error' : ''}`}
        value={day}
        aria-invalid={Boolean(error)}
        aria-required="true"
        onChange={(e) => handleDay(e.target.value)}
      >
        <option value="">日</option>
        {dayOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}