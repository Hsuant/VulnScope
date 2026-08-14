import service from './request'
import type { TagItem, TagCreatePayload, TagUpdatePayload } from '@/types/tag'

export function listTags(params?: { namespace?: string; page?: number; page_size?: number }): Promise<{ items: TagItem[]; total: number }> {
  return service.get('/tags', { params })
}

export function getTag(id: number): Promise<TagItem> {
  return service.get(`/tags/${id}`)
}

export function createTag(data: TagCreatePayload): Promise<TagItem> {
  return service.post('/tags', data)
}

export function updateTag(id: number, data: TagUpdatePayload): Promise<TagItem> {
  return service.put(`/tags/${id}`, data)
}

export function deleteTag(id: number): Promise<{ deleted: boolean }> {
  return service.delete(`/tags/${id}`)
}

export function listNamespaces(): Promise<string[]> {
  return service.get('/tags/namespaces')
}