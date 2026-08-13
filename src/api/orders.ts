import http, { unwrapData, type ApiEnvelope } from './http'

export interface CreateOrderPayload {
  profileId: string
  productId: number
  paymentMethod?: 'auto' | 'h5' | 'native'
  adParams?: Record<string, string>
}

/** 创建订单响应：支付未实现时 payType/payUrl/codeUrl 为 null */
export interface OrderResult {
  orderNo: string
  amount: number
  payType: string | null
  payUrl: string | null
  codeUrl: string | null
}

export interface OrderDetail {
  orderNo: string
  profileId: string
  amount: number
  state: string
  payType: string | null
  createdAt?: string
  paidAt?: string | null
}

export interface OrderReport {
  orderNo: string
  state: string
  report: {
    title: string
    score?: number
    rank?: string
    scoreNote?: string
    analysis?: { label: string; text: string }
    karma?: Array<{ title: string; body: string }>
    lockedPreview: Array<{ title: string; body: string }>
    locked?: boolean
    lockedNote?: string
    contentUrl?: string
  }
  wecom: {
    addWay?: string
    qrcodeUrl: string
    state?: string
    note?: string
  } | null
}

export interface DeliveryInfo {
  orderNo: string
  state: string
  wecomAdded: boolean
  addedAt: string | null
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
 * 获取报告（含企微活码）——预留接口，报告页使用
 * GET /api/orders/{orderNo}/report
 */
export async function getOrderReport(orderNo: string): Promise<OrderReport> {
  const { data } = await http.get<ApiEnvelope<OrderReport>>(
    `/orders/${orderNo}/report`,
  )
  return unwrapData(data)
}

/**
 * 交付状态/企微添加状态——预留接口
 * GET /api/orders/{orderNo}/delivery
 */
export async function getDelivery(orderNo: string): Promise<DeliveryInfo> {
  const { data } = await http.get<ApiEnvelope<DeliveryInfo>>(
    `/orders/${orderNo}/delivery`,
  )
  return unwrapData(data)
}
