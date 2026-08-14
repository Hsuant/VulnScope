import service from './request'
import type { PocListItem, PocDetail, PocVersion, PocCreatePayload, PocUpdatePayload, PocImportResult, PocSourceRecord } from '@/types/poc'

export interface PocListParams {
  page?: number
  page_size?: number
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
}

export function listPocs(params: PocListParams): Promise<{ items: PocListItem[]; total: number; page: number; page_size: number; total_pages: number }> {
  return service.get('/pocs', { params })
}

export function searchPocs(q: string, page = 1, page_size = 20): Promise<{ items: PocListItem[]; total: number }> {
  return service.get('/pocs/search', { params: { q, page, page_size } })
}

export function getPoc(id: number): Promise<PocDetail> {
  return service.get(`/pocs/${id}`)
}

export function createPoc(data: PocCreatePayload): Promise<PocDetail> {
  return service.post('/pocs', data)
}

export function updatePoc(id: number, data: PocUpdatePayload): Promise<PocDetail> {
  return service.put(`/pocs/${id}`, data)
}

export function deletePoc(id: number): Promise<{ deleted: boolean }> {
  return service.delete(`/pocs/${id}`)
}

export function changePocStatus(id: number, status: string): Promise<PocDetail> {
  return service.patch(`/pocs/${id}/status`, { status })
}

export function clonePoc(id: number, name: string): Promise<PocDetail> {
  return service.post(`/pocs/${id}/clone`, { name })
}

export function getPocVersions(id: number): Promise<PocVersion[]> {
  return service.get(`/pocs/${id}/versions`)
}

export function getPocSourceRecords(id: number): Promise<PocSourceRecord[]> {
  return service.get(`/pocs/${id}/source-records`)
}

export function verifyUrl(url: string): Promise<{ url: string; reachable: boolean; status_code: number; error: string | null }> {
  return service.post('/pocs/verify-url', { url })
}