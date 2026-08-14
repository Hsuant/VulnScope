export interface VulnItem {
  id: number
  cve_id: string
  title: string | null
  description: string | null
  cvss: number | null
  severity: string | null
  poc_count: number
  created_at: string | null
}