/** URL 安全校验：防 javascript:/data: 等协议劫持 */

const ALLOWED_URL_PATTERN = /^https:\/\//i

// 支付/活码允许的域名白名单（前缀匹配）
const PAY_ALLOW_HOSTS = ["wx.tenpay.com", "work.weixin.qq.com", "qywx."]
const QRCODE_ALLOW_HOSTS = ["work.weixin.qq.com", "qywx."]

function hostAllowed(host: string, allowList: string[]): boolean {
  const h = host.toLowerCase()
  return allowList.some((a) => {
    const low = a.toLowerCase()
    if (low.endsWith(".")) {
      // 前缀匹配：如 "qywx." 匹配 "qywx.qq.com"、"qywx.com" 前缀
      return h.startsWith(low)
    }
    return h === low || h.endsWith("." + low)
  })
}

/** 校验是否为安全的 https URL，且主机在白名单（若提供白名单） */
export function isSafeHttpUrl(url: string | null | undefined, allowHosts?: string[]): boolean {
  if (!url || typeof url !== "string") return false
  if (!ALLOWED_URL_PATTERN.test(url.trim())) return false
  try {
    const u = new URL(url)
    if (u.protocol !== "https:") return false
    if (allowHosts && allowHosts.length > 0) {
      if (!hostAllowed(u.hostname, allowHosts)) return false
    }
    return true
  } catch {
    return false
  }
}

export function isSafePayUrl(url: string | null | undefined): boolean {
  return isSafeHttpUrl(url, PAY_ALLOW_HOSTS)
}

export function isSafeQrcodeUrl(url: string | null | undefined): boolean {
  return isSafeHttpUrl(url, QRCODE_ALLOW_HOSTS)
}

export function isSafeCodeUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== "string") return false
  const t = url.trim()
  if (t.startsWith("weixin://")) return true
  return isSafeHttpUrl(t)
}
