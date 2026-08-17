import service from './request'
import type { VulnItem } from '@/types/vuln'

export function listVulns(params?: { page?: number; page_size?: number; severity?: string; q?: string }): Promise<{ items: VulnItem[]; total: number }> {
  return service.get('/vulns', { params })
}

export function getVuln(id: number): Promise<VulnItem> {
  return service.get(`/vulns/${id}`)
}

export function getVulnByCveId(cve_id: string): Promise<VulnItem> {
  return service.get(`/vulns/by-cve/${cve_id}`)
}

export function deleteVuln(id: number): Promise<{ deleted: boolean }> {
  return service.delete(`/vulns/${id}`)
}

export function deleteVulnsBatch(ids: number[]): Promise<{ deleted_count: number }> {
  return service.delete('/vulns', { data: { ids } })
}