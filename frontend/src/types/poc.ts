export interface TagBrief {
  id: number
  namespace: string
  name: string
  color: string | null
}

export interface CategoryBrief {
  id: number
  name: string
  slug: string
}

export interface PocListItem {
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
  tags: TagBrief[]
  cve_ids: string[]
  cnvd_ids: string[]
  created_at: string | null
  updated_at: string | null
}

export interface PocDetail extends PocListItem {
  description: string | null
  language: string | null
  content: string
  content_hash: string
  extra_meta: Record<string, any> | null
  categories: CategoryBrief[]
  affected_versions: AffectedVersion[]
  references: Reference[]
  fofa_syntax: string | null
  shodan_syntax: string | null
  publicwww_syntax: string | null
  created_by: number | null
  updated_by: number | null
}

export interface AffectedVersion {
  version_start: string | null
  version_start_type: string
  version_end: string | null
  version_end_type: string
}

export interface Reference {
  url: string
  label?: string | null
}

export interface PocVersion {
  id: number
  version_seq: number
  content_hash: string
  changed_by: number | null
  changed_at: string | null
}

export interface PocCreatePayload {
  name: string
  title?: string
  description?: string
  severity: string
  format: string
  language?: string
  content: string
  author?: string
  source: string
  status: string
  cve_ids?: string[]
  cnvd_ids?: string[]
  references?: Reference[]
  fofa_syntax?: string
  shodan_syntax?: string
  publicwww_syntax?: string
  tag_ids?: number[]
  category_ids?: number[]
  affected_versions?: AffectedVersion[]
  extra_meta?: Record<string, any>
}

export interface PocUpdatePayload {
  name?: string
  title?: string
  description?: string
  severity?: string
  format?: string
  language?: string
  content?: string
  author?: string
  source?: string
  status?: string
  cve_ids?: string[]
  cnvd_ids?: string[]
  references?: Reference[]
  fofa_syntax?: string
  shodan_syntax?: string
  publicwww_syntax?: string
  tag_ids?: number[]
  category_ids?: number[]
  affected_versions?: AffectedVersion[]
  extra_meta?: Record<string, any>
}

export interface PocImportResult {
  total: number
  success: number
  skipped: number
  failed: Array<{ name?: string; error: string }>
}

export interface PocSourceRecord {
  id: number
  source_type: string
  batch_id: string | null
  source_url: string | null
  ref_id: string | null
  fetched_at: string | null
  extra_meta: Record<string, any> | null
}

export interface PocQueryParams {
  page: number
  page_size: number
  sort_by?: string
  sort_order?: string
  severity?: string
  status?: string
  source?: string
  format?: string
  author?: string
  tag_ids?: string
  cve?: string
  category_id?: number
  created_at_from?: string
  created_at_to?: string
  q?: string
  search_content?: boolean
}