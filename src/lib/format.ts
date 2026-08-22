/** 分 → 元格式化，保留1位小数，如 990 → ¥9.9 */
export function formatPrice(cents: number): string {
  const yuan = (Number(cents) || 0) / 100
  return `¥${yuan.toFixed(1)}`
}

/**
 * 姓名脱敏：保留首字，其余打星号（张三 → 张*，张三四 → 张**）
 */
export function maskName(name: string): string {
  const chars = (name ?? '').trim().split('')
  if (chars.length === 0) return ''
  return chars[0] + '*'.repeat(Math.max(chars.length - 1, 1))
}

/** 日期只显年月：2026-08-11 → 2026年8月；解析失败返回空串 */
export function formatYearMonth(date: string): string {
  const m = /^(\d{4})-(\d{1,2})/.exec((date ?? '').trim())
  if (!m) return ''
  return `${m[1]}年${Number(m[2])}月`
}
