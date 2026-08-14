import service from './request'
import type { PocImportResult } from '@/types/poc'

export function importPocs(data: FormData): Promise<PocImportResult> {
  return service.post('/import', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function exportPocs(ids: number[], format = 'json'): Promise<{ content: string; format: string; count: number }> {
  return service.get('/export', { params: { ids: ids.join(','), format } })
}