import service from './request'
import type { AuditLogItem } from '@/types/audit'

export interface AuditLogParams {
  page?: number
  page_size?: number
  action?: string
  resource_type?: string
  user_id?: number
}

export function listAuditLogs(params: AuditLogParams): Promise<{ items: AuditLogItem[]; total: number }> {
  return service.get('/audit-logs', { params })
}