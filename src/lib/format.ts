/** 分 → 元格式化，保留1位小数，如 990 → ¥9.9 */
export function formatPrice(cents: number): string {
  const yuan = (Number(cents) || 0) / 100
  return `¥${yuan.toFixed(1)}`
}
