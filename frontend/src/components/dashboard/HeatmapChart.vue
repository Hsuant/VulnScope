<template>
  <!--
    CVE 厂商×CVSS 评分 热力图：
    横轴为厂商（Top-N），纵轴为 CVSS 评分分桶，单元格颜色深浅表示该格 CVE 数量。
    数据由后端 VulnHeatmapAggregator 聚合，本组件仅负责"数据 → ECharts 配置"的渲染。

    样式设计：
    - 仅渲染非零格子（稀疏矩阵），空位以斑马底色透出，画面更通透。
    - 色阶复用项目严重级别色（info→critical），数量越多越接近 critical 红，语义一致。
    - 色阶图例改用自绘 HTML 渐变条（非 ECharts visualMap 控件），宽度自适应、
      彻底规避 visualMap 控件在不同尺寸下渲染出竖线状伪影的问题。
    - 悬浮提示补充"严重级别"推断，并配同色徽标，信息层次分明。
  -->
  <div class="chart-box">
    <template v-if="!isEmpty">
      <!-- 自绘色阶图例：少 → 渐变条 → 多，宽度随面板自适应铺满 -->
      <div class="legend-bar">
        <span class="legend-end">少</span>
        <span class="legend-track" :style="{ background: legendGradient }" />
        <span class="legend-end">多</span>
      </div>
      <div class="chart-canvas">
        <VChart :option="option" autoresize />
      </div>
    </template>
    <div v-else class="chart-empty">暂无数据</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '@/utils/echarts'
import { useChartTheme, type ChartColorKey, type ChartTheme } from '@/composables/useChartTheme'
import type { VulnHeatmapData } from '@/types/dashboard'

/** 热力图单元格三元组：[x_index, y_index, count]。 */
type HeatCell = [number, number, number]

/**
 * 热力图 ECharts 配置构建器。
 *
 * 职责：将后端返回的 (厂商 × CVSS 评分) 二维矩阵转换为 ECharts heatmap
 * 所需的 option，并应用项目主题色（随深/浅色模式自动切换）。
 *
 * 设计遵循单一职责原则：本类只承担"数据 → 配置"的纯转换，不触碰 DOM、
 * 不持有响应式状态，便于单元测试与跨组件复用。
 */
class HeatmapOptionBuilder {
  private readonly data: VulnHeatmapData
  private readonly t: ChartTheme

  /**
   * @param data 后端聚合的热力图数据。
   * @param theme 当前已解析的主题色（含文本、背景、严重级别色阶）。
   */
  constructor(data: VulnHeatmapData, theme: ChartTheme) {
    this.data = data
    this.t = theme
  }

  /** 数据是否为空：无厂商或无非零格子时无可渲染内容。 */
  get isEmpty(): boolean {
    return this.data.x_labels.length === 0 || this.nonzeroCells().length === 0
  }

  /** 入口：构建完整 ECharts option。 */
  build(): Record<string, unknown> {
    return {
      tooltip: this.buildTooltip(),
      grid: this.buildGrid(),
      xAxis: this.buildXAxis(),
      yAxis: this.buildYAxis(),
      visualMap: this.buildVisualMap(),
      series: [this.buildSeries()],
    }
  }

  // ── 数据加工 ───────────────────────────────────────────────────

  /** 仅保留非零格子，稀疏渲染使空位透出底色，画面更通透。 */
  private nonzeroCells(): HeatCell[] {
    return this.data.cells.filter((c): c is HeatCell => c[2] > 0)
  }

  /** 计算单元格最大值，至少为 1，避免 max=0 时色阶退化。 */
  private computeMax(): number {
    const max = this.nonzeroCells().reduce((m, c) => Math.max(m, c[2]), 0)
    return Math.max(max, 1)
  }

  /**
   * 色阶：由低到高复用严重级别色（info→critical），
   * 使"数量越多越接近 critical 红"具备语义一致性，并与全站配色统一。
   */
  colorRamp(): string[] {
    return [
      this.t.colors.info,
      this.t.colors.low,
      this.t.colors.medium,
      this.t.colors.high,
      this.t.colors.critical,
    ]
  }

  /**
   * 将十六进制色值解析为 RGB 三元组，用于构造半透明色（如阴影）。
   * 兼容 3 位与 6 位写法。
   */
  private static hexToRgb(hex: string): [number, number, number] {
    const h = hex.replace('#', '')
    const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
    const n = parseInt(full, 16)
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
  }

  /** 按 RGB 分量与透明度生成阴影色，用于悬浮高亮阴影，提升层次感。 */
  private shadow(colorKey: ChartColorKey, alpha: number): string {
    const [r, g, b] = HeatmapOptionBuilder.hexToRgb(this.t.colors[colorKey])
    return `rgba(${r},${g},${b},${alpha})`
  }

  /**
   * 依据 CVSS 分桶纵轴索引推断严重级别文案。
   * 索引 0=未评分；1..11 对应评分 0..10，按 CVSS v3.x 标准分级。
   */
  private bucketSeverity(yi: number): string {
    if (yi === 0) return '未评级'
    const s = yi - 1
    if (s === 0) return '无'
    if (s <= 3) return '低危'
    if (s <= 6) return '中危'
    if (s <= 8) return '高危'
    return '严重'
  }

  /** 依据 CVSS 分桶纵轴索引返回对应严重级别主题色。 */
  private bucketSeverityColor(yi: number): string {
    if (yi === 0) return this.t.colors.info
    const s = yi - 1
    if (s === 0) return this.t.colors.info
    if (s <= 3) return this.t.colors.low
    if (s <= 6) return this.t.colors.medium
    if (s <= 8) return this.t.colors.high
    return this.t.colors.critical
  }

  // ── option 子结构 ──────────────────────────────────────────────

  /** 气泡提示框：厂商 + CVSS 区间（含严重级别徽标）+ 该格 CVE 数。 */
  private buildTooltip(): Record<string, unknown> {
    return {
      trigger: 'item',
      backgroundColor: this.t.bgSecondary,
      borderColor: this.t.borderSubtle,
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: this.t.textPrimary, fontSize: 12 },
      // params.value 为 [x_index, y_index, count]
      formatter: (params: { value: HeatCell }): string => {
        const [xi, yi, count] = params.value
        const vendor = this.data.x_labels[xi] ?? '未知'
        const bucket = this.data.y_labels[yi] ?? '-'
        const sev = this.bucketSeverity(yi)
        const sevColor = this.bucketSeverityColor(yi)
        return `
          <div style="font-weight:600;font-size:12px;margin-bottom:6px">${vendor}</div>
          <div style="font-size:11px;color:${this.t.textSecondary}">CVSS ${bucket}
            <span style="display:inline-block;margin-left:6px;padding:1px 6px;border-radius:3px;
              color:${sevColor};background:${this.shadow(
                this.severityKey(yi), 0.16,
              )};font-weight:600;font-size:10px">${sev}</span>
          </div>
          <div style="font-size:11px;margin-top:4px;color:${this.t.textSecondary}">CVE 数
            <b style="color:${this.t.textPrimary};font-size:14px;margin-left:4px">${count}</b>
          </div>`
      },
    }
  }

  /** 严重级别键（用于构造徽标底色的 shadow 调用）。 */
  private severityKey(yi: number): ChartColorKey {
    if (yi === 0) return 'info'
    const s = yi - 1
    if (s === 0) return 'info'
    if (s <= 3) return 'low'
    if (s <= 6) return 'medium'
    if (s <= 8) return 'high'
    return 'critical'
  }

  /** 网格留白：色阶图例已移至组件外层 HTML，图表内顶部仅需少量留白。 */
  private buildGrid(): Record<string, unknown> {
    return { top: 8, left: 8, right: 20, bottom: 14, containLabel: true }
  }

  /** 横轴：厂商名过长时旋转并截断，保证可读与整齐。 */
  private buildXAxis(): Record<string, unknown> {
    return {
      type: 'category',
      data: this.data.x_labels,
      axisLine: { lineStyle: { color: this.t.borderSubtle } },
      axisTick: { show: false },
      // 显式关闭纵向网格线与纵向分割区，杜绝竖线伪影。
      splitLine: { show: false },
      splitArea: { show: false },
      axisLabel: {
        color: this.t.textSecondary,
        fontSize: 11,
        fontWeight: 500,
        interval: 0,
        rotate: 32,
        width: 84,
        overflow: 'truncate',
        hideOverlap: false,
      },
    }
  }

  /**
   * 纵轴：CVSS 评分分桶。
   * y_labels 顺序为 ['未评分','0',...,'10']，ECharts 默认索引 0 在底部，
   * 因此高分（10）自然置于顶部，符合"越严重越靠上"的阅读直觉。
   * 斑马底色用于透出空格子区域，形成清晰矩阵网格（横向带状，非竖线）。
   */
  private buildYAxis(): Record<string, unknown> {
    return {
      type: 'category',
      data: this.data.y_labels,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { color: this.t.textSecondary, fontSize: 11, fontWeight: 500 },
      splitArea: {
        show: true,
        areaStyle: { color: [this.t.bgSecondary, this.t.bgTertiary] },
      },
    }
  }

  /**
   * 视觉映射：仅用于将 CVE 计数映射到色阶（show:false 隐藏 ECharts 自带
   * 色阶控件），改由组件外层自绘 HTML 渐变图例展示，避免控件在不同尺寸下
   * 渲染出竖线状伪影。
   */
  private buildVisualMap(): Record<string, unknown> {
    return {
      min: 0,
      max: this.computeMax(),
      show: false,
      inRange: { color: this.colorRamp() },
    }
  }

  /** 热力图主系列：圆角格子 + 数值标签 + 悬浮高亮阴影。 */
  private buildSeries(): Record<string, unknown> {
    return {
      type: 'heatmap',
      data: this.nonzeroCells(),
      progressive: 200,
      animationDuration: 600,
      animationEasing: 'cubicOut',
      label: {
        show: true,
        color: this.t.textPrimary,
        fontSize: 11,
        fontWeight: 600,
        textShadowColor: 'rgba(0,0,0,0.45)',
        textShadowBlur: 3,
        formatter: (p: { value: HeatCell }) =>
          p.value[2] > 0 ? String(p.value[2]) : '',
      },
      itemStyle: {
        // 与面板同色边框形成清晰分隔线；轻微圆角提升精致度。
        borderColor: this.t.bgSecondary,
        borderWidth: 2,
        borderRadius: 3,
      },
      emphasis: {
        // 悬浮高亮：提亮描边并投下同色柔光，增强层次。
        itemStyle: {
          borderColor: this.t.textSecondary,
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: this.shadow('accent', 0.45),
        },
        label: { fontSize: 12, fontWeight: 700 },
      },
    }
  }
}

const props = defineProps<{
  /** 后端聚合的厂商×CVSS 热力图数据。 */
  data: VulnHeatmapData
}>()

const theme = useChartTheme()

// 由构建器实例化 option；数据或主题变化时自动重算。
const builder = computed(() => new HeatmapOptionBuilder(props.data, theme.value))
const option = computed(() => builder.value.build())
const isEmpty = computed(() => builder.value.isEmpty)

// 自绘图例渐变：与 visualMap.inRange 色阶完全一致，随主题切换。
const legendGradient = computed(
  () => `linear-gradient(to right, ${builder.value.colorRamp().join(',')})`,
)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.chart-box {
  width: 100%;
  height: 340px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

// ── 自绘色阶图例 ───────────────────────────────────────────────
.legend-bar {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: 0 4px;
}

.legend-end {
  font-size: 10px;
  color: $text-secondary;
  flex-shrink: 0;
}

.legend-track {
  flex: 1;
  height: 9px;
  border-radius: $radius-md;
  border: 1px solid $border-subtle;
}

// ── 图表画布 ───────────────────────────────────────────────────
.chart-canvas {
  flex: 1;
  min-height: 0;
}

.chart-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
  font-size: $font-caption;
}
</style>
