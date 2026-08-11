import http from './http'

export interface CreateProfileRequest {
  nameA: string
  birthA: string
  birthHourA?: string
  nameB: string
  birthB: string
  birthHourB?: string
  isLunar?: boolean
}

export interface PreviewReport {
  title: string
  contentUrl: string
  locked: boolean
  lockedNote?: string
}

export interface CreateProfileResult {
  profileId: string
  previewReport: PreviewReport
}

interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

/** 生成幂等键（POST 写操作重试安全） */
export function newIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `ik-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/**
 * 提交测算信息并生成预览报告
 * POST /api/profiles
 */
export async function createProfile(
  payload: CreateProfileRequest,
  idempotencyKey: string,
): Promise<CreateProfileResult> {
  const { data } = await http.post<ApiEnvelope<CreateProfileResult>>(
    '/profiles',
    payload,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  if (data.code !== 0) {
    throw new Error(data.message || '提交失败，请稍后重试')
  }
  return data.data
}
