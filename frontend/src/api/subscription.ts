import service from './request'

export interface SubscriptionItem {
  id: number
  user_id: number
  sub_type: string
  target_id: string
  target_display: string | null
  notify_on_update: boolean
  notify_on_new: boolean
  created_at: string | null
}

export interface SubscriptionCreatePayload {
  sub_type: 'cve' | 'vendor' | 'tag'
  target_id: string
  notify_on_update?: boolean
  notify_on_new?: boolean
}

export interface SubscriptionUpdatePayload {
  notify_on_update?: boolean
  notify_on_new?: boolean
}

/** 创建订阅 */
export function createSubscription(data: SubscriptionCreatePayload): Promise<SubscriptionItem> {
  return service.post('/subscriptions', data)
}

/** 订阅列表 */
export function listSubscriptions(params: {
  page?: number
  page_size?: number
}): Promise<{ items: SubscriptionItem[]; total: number; page: number; page_size: number; total_pages: number }> {
  return service.get('/subscriptions', { params })
}

/** 更新订阅 */
export function updateSubscription(id: number, data: SubscriptionUpdatePayload): Promise<SubscriptionItem> {
  return service.put(`/subscriptions/${id}`, data)
}

/** 取消订阅 */
export function deleteSubscription(id: number): Promise<{ deleted: boolean; subscription_id: number }> {
  return service.delete(`/subscriptions/${id}`)
}