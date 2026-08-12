import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api'

/** 统一响应信封（后端约定见 doc/API接口规范模板.md §1.4） */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

/**
 * 解包统一信封：code!==0 视为业务失败并抛出可展示的错误信息。
 * 供各 API 模块复用，保持一致的错误处理。
 */
export function unwrapData<T>(env: ApiEnvelope<T>): T {
  if (env.code !== 0) {
    throw new Error(env.message || '请求失败，请稍后重试')
  }
  return env.data
}

const http = axios.create({
  baseURL,
  timeout: 10000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error)
  },
)

export default http
