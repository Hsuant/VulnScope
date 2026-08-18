<template>
  <div class="dashboard-view">
    <PageHeader title="工作台" />

    <div v-loading="loading" class="dashboard-content">
      <!-- ── 关键指标 KPI 条 ─────────────────────────────────────── -->
      <section class="kpi-strip">
        <div v-for="k in kpiCards" :key="k.key" class="kpi-card" :class="'kpi-' + k.key">
          <div class="kpi-icon">
            <el-icon :size="22"><component :is="k.icon" /></el-icon>
          </div>
          <div class="kpi-main">
            <span class="kpi-value">{{ k.value }}</span>
            <span class="kpi-label">{{ k.label }}</span>
          </div>
          <span v-if="k.sub" class="kpi-sub">{{ k.sub }}</span>
        </div>
      </section>

      <!-- ── 趋势 + 状态环 ─────────────────────────────────────── -->
      <section class="grid">
        <div class="panel panel--trend span-8">
          <div class="panel-head">
            <div>
              <h3 class="panel-title">POC / CVE 新增趋势</h3>
              <p class="panel-sub">近 30 天每日新增 · 累计 POC {{ trendSum }} 个</p>
            </div>
          </div>
          <TrendChart :points="trendData" />
        </div>

        <div class="panel span-4">
          <div class="panel-head"><h3 class="panel-title">POC 状态分布</h3></div>
          <div class="donut-wrap">
            <DonutChart :items="statusItems" :total="stats.total_pocs" center-label="POC" />
            <div class="legend-col">
              <div v-for="s in statusItems" :key="s.name" class="legend-row">
                <span class="legend-dot" :style="{ background: cssVar(s.colorKey) }" />
                <span class="legend-text">{{ s.name }}</span>
                <span class="legend-val">{{ s.value }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── 严重级别 / 可选命名空间标签分布 / 资产搜集命令分布 ── -->
      <section class="grid">
        <div class="panel span-4">
          <div class="panel-head"><h3 class="panel-title">严重级别分布</h3></div>
          <BarChart :items="severityItems" />
        </div>

        <div class="panel span-4">
          <div class="panel-head">
            <h3 class="panel-title">命名空间标签分布</h3>
            <span class="panel-meta">共 {{ tagDistRaw.length }} 个标签</span>
          </div>
          <div class="ns-selector-wrap">
            <el-select
              v-model="selectedNamespace"
              :loading="nsLoading"
              size="small"
              placeholder="选择命名空间"
              class="ns-selector"
              @change="loadTagDistribution"
            >
              <el-option
                v-for="ns in namespaces"
                :key="ns"
                :label="ns"
                :value="ns"
              />
            </el-select>
          </div>
          <div class="tag-pie-wrap">
            <DonutChart :items="tagDistItems" variant="pie" show-labels />
          </div>
        </div>

        <div class="panel span-4">
          <div class="panel-head"><h3 class="panel-title">资产搜集命令分布</h3></div>
          <BarChart :items="assetSearchItems" />
        </div>
      </section>

      <!-- ── CVE 厂商×CVSS 热力图 / 高产作者 / 最近活动 ──────────── -->
      <section class="grid">
        <div class="panel span-8">
          <div class="panel-head">
            <h3 class="panel-title">厂商 × CVSS 风险矩阵</h3>
            <span class="panel-meta">色越深 · 该格 CVE 越多</span>
          </div>
          <HeatmapChart :data="heatmapData" />
        </div>

        <div class="panel span-4">
          <div class="panel-head">
            <h3 class="panel-title">高产作者</h3>
            <span class="panel-meta">{{ stats.total_authors }} 位贡献者</span>
          </div>
          <div v-if="authorData.length" class="rank-list">
            <div v-for="(item, i) in authorData" :key="item.author" class="rank-row">
              <span class="rank-no" :class="{ 'rank-top': i < 3 }">{{ i + 1 }}</span>
              <span class="rank-name" :title="item.author">{{ item.author }}</span>
              <div class="rank-track">
                <div class="rank-fill" :style="{ width: authorPercent(item.count) }" />
              </div>
              <span class="rank-count">{{ item.count }}</span>
            </div>
          </div>
          <div v-else class="chart-empty">暂无作者数据</div>
        </div>
      </section>

      <!-- ── 最近活动 ─────────────────────────────────────────────── -->
      <section class="grid">
        <div class="panel span-12">
          <div class="panel-head"><h3 class="panel-title">最近活动</h3></div>
          <div v-if="activityData.length" class="activity-timeline">
            <div v-for="item in activityData" :key="item.timestamp" class="activity-node">
              <span class="activity-dot" :style="{ background: actionColor(item.action) }" />
              <div class="activity-body">
                <span class="activity-name">{{ item.poc_name || '未知 POC' }}</span>
                <span class="activity-action">{{ actionLabel(item.action) }}</span>
              </div>
              <span class="activity-time">{{ formatDateTime(item.timestamp) }}</span>
            </div>
          </div>
          <div v-else class="chart-empty">暂无活动记录</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getFullDashboard, getTagNamespaceDistribution } from '@/api/dashboard'
import { listNamespaces } from '@/api/tag'
import { SEVERITY_MAP, STATUS_MAP, ACTION_MAP } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import TrendChart from '@/components/dashboard/TrendChart.vue'
import DonutChart, { type DonutItem } from '@/components/dashboard/DonutChart.vue'
import BarChart, { type BarItem } from '@/components/dashboard/BarChart.vue'
import HeatmapChart from '@/components/dashboard/HeatmapChart.vue'
import { cssVar, type ChartColorKey } from '@/composables/useChartTheme'
import type { DashboardData, VulnHeatmapData } from '@/types/dashboard'

const loading = ref(true)
const data = ref<DashboardData | null>(null)

// ── 命名空间选择 ──────────────────────────────────────────────────
const namespaces = ref<string[]>([])
const nsLoading = ref(false)
const selectedNamespace = ref<string>('')
const tagDistRaw = ref<{ tag_name: string; count: number }[]>([])

async function loadNamespaces() {
  nsLoading.value = true
  try {
    namespaces.value = await listNamespaces()
    if (namespaces.value.length && !selectedNamespace.value) {
      selectedNamespace.value = namespaces.value[0]
      await loadTagDistribution()
    }
  } catch {
    // handled by interceptor
  } finally {
    nsLoading.value = false
  }
}

async function loadTagDistribution() {
  if (!selectedNamespace.value) return
  try {
    tagDistRaw.value = await getTagNamespaceDistribution(selectedNamespace.value)
  } catch {
    tagDistRaw.value = []
  }
}

// ── 色彩键映射：数据键 → CSS 变量名（图例用 var()，ECharts 用解析色） ─
const SEVERITY_KEY: Record<string, ChartColorKey> = { critical: 'critical', high: 'high', medium: 'medium', low: 'low', info: 'info' }
const STATUS_KEY: Record<string, ChartColorKey> = { active: 'active', draft: 'info', disabled: 'disabled', archived: 'archived' }
const TAG_NS_COLORS: ChartColorKey[] = ['accent', 'active', 'archived', 'medium', 'low', 'high', 'critical', 'info']

const ASSET_SEARCH_LABEL: Record<string, string> = {
  fofa: 'FOFA', shodan: 'Shodan', publicwww: 'PublicWWW',
}
const ACTION_KEY: Record<string, ChartColorKey> = {
  'poc.created': 'active',
  'poc.updated': 'accent',
  'poc.deleted': 'disabled',
  'poc.status_changed': 'medium',
  'poc.version_created': 'archived',
  'poc.batch_imported': 'low',
}
function actionColor(action: string): string {
  return cssVar(ACTION_KEY[action] || 'accent')
}

// ── 统计 ────────────────────────────────────────────────────────
const stats = computed(() => data.value?.stats || {
  total_pocs: 0, total_active_pocs: 0, total_vulns: 0, total_tags: 0, total_categories: 0, total_authors: 0,
})

const trendData = computed(() => data.value?.vulnerability_trend || [])
const trendSum = computed(() => trendData.value.reduce((s, p) => s + p.new_pocs, 0))
const activeRate = computed(() =>
  stats.value.total_pocs ? Math.round((stats.value.total_active_pocs / stats.value.total_pocs) * 100) : 0,
)
const vulnsPerPoc = computed(() =>
  stats.value.total_pocs ? (stats.value.total_vulns / stats.value.total_pocs).toFixed(1) : '0',
)
const pocsPerAuthor = computed(() =>
  stats.value.total_authors ? Math.round(stats.value.total_pocs / stats.value.total_authors) : 0,
)

const kpiCards = computed(() => [
  { key: 'pocs', icon: 'Document', label: 'POC 总数', value: stats.value.total_pocs, sub: `近 30 天 +${trendSum.value}` },
  { key: 'active', icon: 'CircleCheckFilled', label: '活跃 POC', value: stats.value.total_active_pocs, sub: `活跃率 ${activeRate.value}%` },
  { key: 'vulns', icon: 'WarningFilled', label: 'CVE 漏洞', value: stats.value.total_vulns, sub: `平均 ${vulnsPerPoc.value} / POC` },
  { key: 'authors', icon: 'UserFilled', label: '贡献者', value: stats.value.total_authors, sub: `人均 ${pocsPerAuthor.value} POC` },
])

// ── 图表数据（含名称与色彩键） ──────────────────────────────────
const severityItems = computed<BarItem[]>(() => {
  if (!data.value) return []
  const order = ['critical', 'high', 'medium', 'low', 'info']
  return order
    .map(k => data.value!.severity_distribution.find(d => d.key === k))
    .filter((d): d is NonNullable<typeof d> => !!d)
    .map(d => ({ name: SEVERITY_MAP[d.key] || d.key, value: d.count, colorKey: SEVERITY_KEY[d.key] || 'accent' }))
})

const statusItems = computed<DonutItem[]>(() => {
  if (!data.value) return []
  const order = ['active', 'draft', 'disabled', 'archived']
  return order
    .map(k => data.value!.status_distribution.find(d => d.key === k))
    .filter((d): d is NonNullable<typeof d> => !!d)
    .map(d => ({ name: STATUS_MAP[d.key] || d.key, value: d.count, colorKey: STATUS_KEY[d.key] || 'accent' }))
})

// 命名空间标签全量展示（不折叠为"其他"），每项配循环色键。
const tagDistItems = computed<DonutItem[]>(() =>
  tagDistRaw.value.map((d, i) => ({
    name: d.tag_name,
    value: d.count,
    colorKey: TAG_NS_COLORS[i % TAG_NS_COLORS.length],
  })),
)

const assetSearchItems = computed<BarItem[]>(() => {
  if (!data.value) return []
  return data.value!.asset_search_distribution.map(d => ({
    name: ASSET_SEARCH_LABEL[d.key] || d.key.toUpperCase(),
    value: d.count,
    colorKey: 'accent',
  }))
})

const heatmapData = computed<VulnHeatmapData>(() => {
  const h = data.value?.vuln_vendor_cvss_heatmap
  return h ?? { x_labels: [], y_labels: [], cells: [] }
})

const authorData = computed(() => data.value?.top_authors || [])
const activityData = computed(() => data.value?.recent_activities || [])

const maxAuthorCount = computed(() => Math.max(...authorData.value.map(t => t.count), 1))
function authorPercent(count: number): string {
  return `${(count / maxAuthorCount.value) * 100}%`
}

function actionLabel(action: string): string {
  return ACTION_MAP[action] || action
}

onMounted(async () => {
  try {
    data.value = await getFullDashboard()
    await loadNamespaces()
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.dashboard-view {
  max-width: 1440px;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

// ── KPI 条 ─────────────────────────────────────────────────────
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
}

.kpi-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-lg $spacing-xl;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(var(--vs-accent-rgb), 0.05), transparent 55%);
    pointer-events: none;
  }

  &.kpi-active::before { background: linear-gradient(135deg, rgba(var(--vs-active-rgb), 0.06), transparent 55%); }
  &.kpi-vulns::before { background: linear-gradient(135deg, rgba(var(--vs-high-rgb), 0.06), transparent 55%); }
  &.kpi-authors::before { background: linear-gradient(135deg, rgba(var(--vs-archived-rgb), 0.06), transparent 55%); }
}

.kpi-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: $radius-md;
  background: rgba(var(--vs-accent-rgb), 0.14);
  color: $accent;
  flex-shrink: 0;
  z-index: 1;

  .kpi-active & { background: rgba(var(--vs-active-rgb), 0.14); color: $active; }
  .kpi-vulns & { background: rgba(var(--vs-high-rgb), 0.14); color: $high; }
  .kpi-authors & { background: rgba(var(--vs-archived-rgb), 0.14); color: $archived; }
}

.kpi-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  z-index: 1;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: $text-primary;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.kpi-label {
  font-size: $font-caption;
  color: $text-secondary;
}

.kpi-sub {
  margin-left: auto;
  padding: 2px 8px;
  font-size: 11px;
  color: $text-secondary;
  background: $bg-tertiary;
  border-radius: 999px;
  white-space: nowrap;
  z-index: 1;
}

// ── 通用面板 ────────────────────────────────────────────────────
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: $spacing-lg;
}

.panel {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-lg $spacing-xl;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.span-4 { grid-column: span 4; }
.span-8 { grid-column: span 8; }
.span-12 { grid-column: span 12; }

.panel--trend {
  background:
    radial-gradient(120% 100% at 100% 0%, rgba(var(--vs-accent-rgb), 0.05), transparent 60%),
    $bg-secondary;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: $spacing-md;
  margin-bottom: $spacing-md;
}

.panel-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  margin: 0;
}

.panel-sub {
  font-size: $font-caption;
  color: $text-secondary;
  margin: 2px 0 0;
}

.panel-meta {
  font-size: $font-caption;
  color: $text-disabled;
  white-space: nowrap;
}

// ── 图例 ───────────────────────────────────────────────────────
.legend-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;

  &.accent { background: $accent; }
}

.legend-text {
  font-size: $font-caption;
  color: $text-secondary;
}

// ── 环形/饼图 + 图例布局 ────────────────────────────────────────
.donut-wrap {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  flex: 1;
}

.legend-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  min-width: 0;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.legend-row .legend-dot {
  width: 9px;
  height: 9px;
}

.legend-row .legend-text {
  flex: 1;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-val {
  color: $text-secondary;
  font-variant-numeric: tabular-nums;
  font-size: $font-caption;
}

// ── 命名空间选择器 ──────────────────────────────────────────────
.ns-selector-wrap {
  margin-bottom: $spacing-sm;
}

.ns-selector {
  width: 100%;
}

// 命名空间标签饼图容器：固定高度与两侧柱状图对齐，饼图引线标签撑满内部空间。
.tag-pie-wrap {
  flex: 1;
  min-height: 0;
  height: 220px;
  display: flex;
}

// ── 排名列表 ───────────────────────────────────────────────────
.rank-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  flex: 1;
}

.rank-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.rank-no {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: $text-secondary;
  background: $bg-tertiary;
  border-radius: 50%;
  flex-shrink: 0;

  &.rank-top {
    background: rgba(var(--vs-accent-rgb), 0.18);
    color: $accent;
  }
}

.rank-name {
  width: 70px;
  font-size: $font-caption;
  color: $text-primary;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-track {
  flex: 1;
  height: 14px;
  background: $bg-tertiary;
  border-radius: $radius-sm;
  overflow: hidden;
}

.rank-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(var(--vs-archived-rgb), 0.4), var(--vs-archived));
  border-radius: $radius-sm;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.rank-count {
  width: 32px;
  font-size: $font-caption;
  color: $text-secondary;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

// ── 活动时间线 ─────────────────────────────────────────────────
.activity-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  flex: 1;
}

.activity-node {
  position: relative;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm 0;
  padding-left: $spacing-md;

  &::before {
    content: '';
    position: absolute;
    left: 3px;
    top: 18px;
    bottom: -8px;
    width: 1px;
    background: $border-subtle;
  }

  &:last-child::before { display: none; }
}

.activity-dot {
  position: absolute;
  left: 0;
  top: 14px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(var(--vs-accent-rgb), 0.12);
}

.activity-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.activity-name {
  font-size: $font-body;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-action {
  font-size: $font-caption;
  color: $text-secondary;
}

.activity-time {
  font-size: $font-caption;
  color: $text-disabled;
  white-space: nowrap;
  flex-shrink: 0;
}

// ── 空状态 ─────────────────────────────────────────────────────
.chart-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
  font-size: $font-body;
}

// ── 响应式 ─────────────────────────────────────────────────────
@media (max-width: 1100px) {
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .span-4 { grid-column: span 6; }
  .span-8 { grid-column: span 12; }
  .span-12 { grid-column: span 12; }
}

@media (max-width: 720px) {
  .kpi-strip { grid-template-columns: 1fr; }
  .span-4, .span-8, .span-12 { grid-column: span 12; }
  .donut-wrap { flex-direction: column; }
}
</style>