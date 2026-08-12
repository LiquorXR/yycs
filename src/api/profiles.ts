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

/**
 * 重新获取预览报告（下单页摘要展示用）。
 * 脱敏字段（nameA/nameB/birthA/birthB）为 A 阶段扩展：
 * 后端未返回时前端仅展示报告标题。
 */
export interface ProfilePreview {
  profileId: string
  previewReport: PreviewReport
  nameA?: string
  nameB?: string
  birthA?: string
  birthB?: string
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

/**
 * 重新获取预览报告（含脱敏测算信息摘要）
 * GET /api/profiles/{profileId}/preview
 */
export async function getProfilePreview(profileId: string): Promise<ProfilePreview> {
  const { data } = await http.get<ApiEnvelope<ProfilePreview>>(
    `/profiles/${profileId}/preview`,
  )
  if (data.code !== 0) {
    throw new Error(data.message || '获取测算信息失败，请稍后重试')
  }
  return data.data
}
