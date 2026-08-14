export interface ApiResponse<T = any> {
  code: string
  message: string
  data: T
  request_id: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}