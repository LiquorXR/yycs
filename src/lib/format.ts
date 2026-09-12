/** 分 → 元格式化，保留1位小数，如 990 → ¥9.9；0 分显示 ¥0 */
export function formatPrice(cents: number): string {
  if (!Number(cents)) return '¥0'
  const yuan = Number(cents) / 100
  return `¥${yuan.toFixed(1)}`
}
