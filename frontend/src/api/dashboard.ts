import service from './request'
import type { DashboardData, DistributionItem, TimelinePoint, TrendPoint, TopAuthor, RecentActivity, VulnTreemapItem, TagDistItem } from '@/types/dashboard'

export function getFullDashboard(): Promise<DashboardData> {
  return service.get('/dashboard/full')
}

export function getStats(): Promise<DashboardData['stats']> {
  return service.get('/dashboard/stats')
}

export function getSeverityDistribution(): Promise<DistributionItem[]> {
  return service.get('/dashboard/severity')
}

export function getStatusDistribution(): Promise<DistributionItem[]> {
  return service.get('/dashboard/status')
}

export function getCreationTimeline(days = 30): Promise<TimelinePoint[]> {
  return service.get('/dashboard/timeline', { params: { days } })
}

export function getTopAuthors(limit = 10): Promise<TopAuthor[]> {
  return service.get('/dashboard/top-authors', { params: { limit } })
}

export function getRecentActivities(limit = 10): Promise<RecentActivity[]> {
  return service.get('/dashboard/recent-activities', { params: { limit } })
}

export function getTrend(days = 30): Promise<TrendPoint[]> {
  return service.get('/dashboard/trend', { params: { days } })
}

export function getTagNamespaceDistribution(namespace: string): Promise<TagDistItem[]> {
  return service.get('/dashboard/tag-distribution', { params: { namespace } })
}

export function getAssetSearchDistribution(): Promise<DistributionItem[]> {
  return service.get('/dashboard/asset-search-distribution')
}

export function getVulnCoverageTreemap(limit = 20): Promise<VulnTreemapItem[]> {
  return service.get('/dashboard/vuln-treemap', { params: { limit } })
}