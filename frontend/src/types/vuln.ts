export interface AffectedProduct {
  vendor: string | null
  product: string | null
  version: string | null
  version_start: string | null
  version_start_type: string | null
  version_end: string | null
  version_end_type: string | null
}

export interface Remediation {
  mitigation: string | null
  workaround: string | null
}

export interface ReferenceLink {
  url: string
  label: string | null
}

export interface PocBrief {
  id: number
  uuid: string
  name: string
  title: string | null
  severity: string
  format: string
  source: string
  status: string
  version: number
}

export interface VulnItem {
  id: number
  cve_id: string
  vendor: string | null
  title: string | null
  description: string | null
  cvss: number | null
  severity: string | null
  cvss_metrics: string | null
  product: AffectedProduct[] | null
  remediation: Remediation | null
  reference: ReferenceLink[] | null
  poc_count: number
  pocs: PocBrief[]
  created_at: string | null
  updated_at: string | null
}

export interface VulnUpdatePayload {
  vendor: string | null
  title: string | null
  description: string | null
  cvss: number | null
  severity: string | null
  cvss_metrics: string | null
  product: AffectedProduct[] | null
  remediation: Remediation | null
  reference: ReferenceLink[] | null
}

export interface VulnCreatePayload {
  cve_id: string
  vendor: string | null
  title: string | null
  description: string | null
  cvss: number | null
  severity: string | null
  cvss_metrics: string | null
  product: AffectedProduct[] | null
  remediation: Remediation | null
  reference: ReferenceLink[] | null
}

export interface VulnImportFailItem {
  name?: string
  error: string
}

export interface VulnImportResult {
  total: number
  success: number
  created: number
  updated: number
  skipped: number
  failed: VulnImportFailItem[]
}
