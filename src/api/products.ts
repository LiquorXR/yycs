import http, { unwrapData, type ApiEnvelope } from './http'

export interface Product {
  id: number
  name: string
  price: number
  type: number
  freeFlag: number
  status: number
}

export interface ProductListResult {
  list: Product[]
  total: number
  page: number
  pageSize: number
}

/**
 * 产品列表
 * GET /api/products
 * @param options.type 产品类型：0-免费档，1-付费档
 */
export async function getProducts(options?: { type?: number }): Promise<Product[]> {
  const { data } = await http.get<ApiEnvelope<ProductListResult>>('/products', {
    params: options,
  })
  return unwrapData(data).list
}

/**
 * 产品详情
 * GET /api/products/{id}
 */
export async function getProduct(id: number | string): Promise<Product> {
  const { data } = await http.get<ApiEnvelope<Product>>(`/products/${id}`)
  return unwrapData(data)
}
