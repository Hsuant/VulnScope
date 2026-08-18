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
  vulnerability_trend: TrendPoint[]
  top_authors: TopAuthor[]
  recent_activities: RecentActivity[]
  asset_search_distribution: DistributionItem[]
  vuln_vendor_cvss_heatmap: VulnHeatmapData
}

/**
 * CVE 厂商×CVSS 评分 热力图数据。
 *
 * - x_labels：横轴厂商名（Top-N，按关联 CVE 数降序）。
 * - y_labels：纵轴 CVSS 评分分桶（未评分 + 0..10，高分在顶）。
 * - cells：[x_index, y_index, count] 三元组（全量矩阵，含 0）。
 */
export interface VulnHeatmapData {
  x_labels: string[]
  y_labels: string[]
  cells: [number, number, number][]
}

export interface TagDistItem {
  tag_name: string
  count: number
}