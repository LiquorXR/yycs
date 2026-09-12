import http, { unwrapData, type ApiEnvelope } from './http'

export interface CreateOrderPayload {
  profileId: string
  productId: number
  paymentMethod?: 'auto' | 'h5'
  adParams?: Record<string, string>
}

/** 创建订单响应：微信小店 H5 单链路；未配置时 payType/payUrl 为 null，codeUrl 恒为 null；限时0元时 payType='free' 且 freeUnlocked=true */
export interface OrderResult {
  orderNo: string
  amount: number
  payType: string | null
  payChannel?: string | null
  payUrl: string | null
  codeUrl: string | null
  /** H5 直达收银台地址（短链解析，best-effort；失败为 null 时回落 payUrl） */
  jumpUrl?: string | null
  /** 微信直跳（weixin:// 小程序，官方中转页同款；失败为 null 时回落） */
  wxJumpUrl?: string | null
  /** 限时0元：已自解锁，无需支付 */
  freeUnlocked?: boolean | null
}

export interface OrderDetail {
  orderNo: string
  profileId: string
  amount: number
  state: string
  payType: string | null
  payChannel?: string | null
  payUrl: string | null
  codeUrl: string | null
  jumpUrl?: string | null
  wxJumpUrl?: string | null
  failReason?: string | null
  createdAt?: string
  paidAt?: string | null
}

/** 报告接口：无论订单状态一律返回 title + lockedPreview + locked=true；完整内容由人工企微交付 */
export interface OrderReport {
  orderNo: string
  state: string
  report: {
    title: string
    lockedPreview: Array<{ title: string; body: string }>
    locked?: boolean
  }
  wecom: {
    addWay?: string
    qrcodeUrl: string
    state?: string
    note?: string
  } | null
}

/**
 * 创建订单（幂等键必填，服务端 24 小时内同键返回首次结果）
 * POST /api/orders
 */
export async function createOrder(
  payload: CreateOrderPayload,
  idempotencyKey: string,
): Promise<OrderResult> {
  const { data } = await http.post<ApiEnvelope<OrderResult>>(
    '/orders',
    payload,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  return unwrapData(data)
}

/**
 * 订单详情/状态
 * GET /api/orders/{orderNo}
 */
export async function getOrder(orderNo: string): Promise<OrderDetail> {
  const { data } = await http.get<ApiEnvelope<OrderDetail>>(`/orders/${orderNo}`)
  return unwrapData(data)
}

/**
 * 获取报告（含企微加好友链接）——报告页使用
 * GET /api/orders/{orderNo}/report
 */
export async function getOrderReport(orderNo: string): Promise<OrderReport> {
  const { data } = await http.get<ApiEnvelope<OrderReport>>(
    `/orders/${orderNo}/report`,
  )
  return unwrapData(data)
}
