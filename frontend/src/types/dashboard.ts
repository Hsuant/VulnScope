export interface DashboardStats {
  total_pocs: number
  total_active_pocs: number
  total_vulns: number
  total_tags: number
  total_categories: number
  total_authors: number
}

export interface DistributionItem {
  key: string
  count: number
}

export interface TimelinePoint {
  date: string
  count: number
}

export interface TrendPoint {
  date: string
  new_pocs: number
  new_vulns: number
}

export interface TopTag {
  tag_name: string
  namespace: string
  count: number
}

export interface TopAuthor {
  author: string
  count: number
}

export interface RecentActivity {
  poc_id: number
  poc_name: string
  action: string
  timestamp: string
}

export interface DashboardData {
  stats: DashboardStats
  severity_distribution: DistributionItem[]
  status_distribution: DistributionItem[]
  source_distribution: DistributionItem[]
  format_distribution: DistributionItem[]
  creation_timeline: TimelinePoint[]
  top_tags: TopTag[]
  top_authors: TopAuthor[]
  recent_activities: RecentActivity[]
}

export interface TagCloud {
  namespace: string
  tags: TopTag[]
}