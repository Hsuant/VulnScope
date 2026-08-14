import service from './request'
import type { PluginItem } from '@/types/plugin'

export function listPlugins(): Promise<PluginItem[]> {
  return service.get('/plugins')
}

export function listPluginsBySlot(slot: string): Promise<PluginItem[]> {
  return service.get(`/plugins/${slot}`)
}