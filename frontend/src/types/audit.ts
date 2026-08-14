export interface AuditLogItem {
  id: number
  user_id: number | null
  username: string
  action: string
  resource_type: string
  resource_id: string | null
  detail: Record<string, any> | null
  ip: string | null
  created_at: string | null
}