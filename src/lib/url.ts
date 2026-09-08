/** URL 安全校验：防 javascript:/data: 等协议劫持 */

const ALLOWED_URL_PATTERN = /^https:\/\//i

// 支付/活码允许的域名白名单（前缀匹配）
const PAY_ALLOW_HOSTS = ["qr.shouqianba.com", "alipay.com", "alipay.cn", "work.weixin.qq.com", "qywx.", "wosai.cn"]
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

// 微信小店直达收银台地址白名单（短链解析目标，显式 host；后端落库前已校验一次）
const JUMP_ALLOW_HOSTS = ["optimus-c-share.shouqianba.com"]

export function isSafeJumpUrl(url: string | null | undefined): boolean {
  return isSafeHttpUrl(url, JUMP_ALLOW_HOSTS)
}

/** 微信直跳：weixin://dl/business/ 小程序路径（官方中转页同款，后端构造） */
export function isSafeWxJumpUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') return false
  const t = url.trim()
  return t.startsWith('weixin://dl/business/?appid=') && t.includes('&path=') && t.includes('&query=')
}

/** 支付宝直跳：ds.alipay.com 桥页转 alipays scheme（官方中转页同款，后端构造） */
const ALI_JUMP_HOSTS = ['ds.alipay.com']

export function isSafeAliJumpUrl(url: string | null | undefined): boolean {
  if (!isSafeHttpUrl(url, ALI_JUMP_HOSTS)) return false
  try {
    return (new URL(url!.trim()).searchParams.get('scheme') ?? '').startsWith('alipays://platformapi/startapp?')
  } catch {
    return false
  }
}

export function isSafeQrcodeUrl(url: string | null | undefined): boolean {
  return isSafeHttpUrl(url, QRCODE_ALLOW_HOSTS)
}

const CODE_ALLOW_HOSTS = ["qr.shouqianba.com", "alipay.com", "alipay.cn"]

export function isSafeCodeUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== "string") return false
  const t = url.trim()
  if (t.startsWith("weixin://") || t.startsWith("alipays://") || t.startsWith("alipay://")) return true
  return isSafeHttpUrl(t, CODE_ALLOW_HOSTS)
}
