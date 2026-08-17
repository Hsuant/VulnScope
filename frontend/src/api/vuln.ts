import service from './request'
import type { VulnCreatePayload, VulnImportResult, VulnItem, VulnUpdatePayload } from '@/types/vuln'

export function listVulns(params?: { page?: number; page_size?: number; severity?: string; q?: string }): Promise<{ items: VulnItem[]; total: number }> {
  return service.get('/vulns', { params })
}

export function getVuln(id: number): Promise<VulnItem> {
  return service.get(`/vulns/${id}`)
}

export function getVulnByCveId(cve_id: string): Promise<VulnItem> {
  return service.get(`/vulns/by-cve/${cve_id}`)
}

export function updateVuln(id: number, data: VulnUpdatePayload): Promise<VulnItem> {
  return service.put(`/vulns/${id}`, data)
}

export function createVuln(data: VulnCreatePayload): Promise<VulnItem> {
  return service.post('/vulns', data)
}

export function importVulns(data: FormData): Promise<VulnImportResult> {
  return service.post('/vulns/import', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function exportVulns(
  ids: number[],
  format = 'json',
): Promise<{ content: string; format: string; count: number }> {
  return service.get('/vulns/export', { params: { ids: ids.join(','), format } })
}

export function deleteVuln(id: number): Promise<{ deleted: boolean }> {
  return service.delete(`/vulns/${id}`)
}

export function deleteVulnsBatch(ids: number[]): Promise<{ deleted_count: number }> {
  return service.delete('/vulns', { data: { ids } })
}