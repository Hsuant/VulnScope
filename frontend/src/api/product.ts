import service from './request'

export interface ProductItem {
  id: number
  slug: string
  name: string
  vendor: string | null
  category: string | null
  homepage: string | null
  description: string | null
  poc_count: number
}

export interface ProductPocItem {
  id: number
  uuid: string
  name: string
  title: string | null
  severity: string
  format: string
  source: string
  status: string
  author: string | null
  version: number
  tags: { id: number; namespace: string; name: string; color: string | null }[]
  cve_ids: string[]
  created_at: string | null
  updated_at: string | null
}

export function listProducts(params?: {
  page?: number
  page_size?: number
  q?: string
  vendor_q?: string
}): Promise<{ items: ProductItem[]; total: number }> {
  return service.get('/products', { params })
}

export function getProductPocs(
  slug: string,
  params?: {
    version?: string
    version_start?: string
    version_start_op?: string
    version_end?: string
    version_end_op?: string
    page?: number
    page_size?: number
  },
): Promise<{ items: ProductPocItem[]; total: number; page: number; page_size: number; total_pages: number }> {
  return service.get(`/products/${slug}/pocs`, { params })
}

export function listVendors(params?: { q?: string }): Promise<{ items: { slug: string; name: string; product_count: number }[] }> {
  return service.get('/products/vendors', { params })
}