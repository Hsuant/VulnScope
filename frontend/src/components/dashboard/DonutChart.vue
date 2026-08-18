<template>
  <!--
    环形/饼图组件，支持两种展示形态：
    - donut/pie + 外部图例（默认，标签关闭）
    - showLabels 模式：直接在饼图上用折线引线标注每个扇区名称，无需外部图例。
  -->
  <div class="donut-chart" :class="{ 'is-full': showLabels }">
    <VChart v-if="items.length" class="donut-canvas" :option="option" autoresize />
    <div v-else class="chart-empty" :class="{ 'is-full': showLabels }">暂无数据</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '@/utils/echarts'
import { useChartTheme, type ChartColorKey } from '@/composables/useChartTheme'

export interface DonutItem {
  name: string
  value: number
  colorKey: ChartColorKey
}

const props = defineProps<{
  items: DonutItem[]
  total?: number
  centerLabel?: string
  variant?: 'donut' | 'pie'
  /** 开启后直接在饼图上以引线标注扇区名称，不再依赖外部图例。 */
  showLabels?: boolean
}>()

const theme = useChartTheme()
const sum = computed(() => props.items.reduce((s, i) => s + i.value, 0))

const option = computed(() => {
  const t = theme.value
  const isDonut = props.variant !== 'pie'
  const showLabels = props.showLabels ?? false
  const data = props.items.map(i => ({
    name: i.name,
    value: i.value,
    itemStyle: { color: t.colors[i.colorKey] || t.colors.accent },
  }))
  return {
    title:
      isDonut && props.centerLabel
        ? {
            text: String(props.total ?? sum.value),
            subtext: props.centerLabel,
            left: 'center',
            top: 'center',
            textStyle: { color: t.textPrimary, fontSize: 24, fontWeight: 700 },
            subtextStyle: { color: t.textSecondary, fontSize: 11 },
            itemStyle: { color: 'transparent' },
          }
        : undefined,
    tooltip: {
      trigger: 'item',
      backgroundColor: t.bgSecondary,
      borderColor: t.borderSubtle,
      textStyle: { color: t.textPrimary },
      formatter: '{b}: {c} ({d}%)',
    },
    series: [
      {
        type: 'pie',
        // showLabels 时缩小半径，为引线与文字腾出外围空间。
        radius: isDonut ? ['62%', '82%'] : showLabels ? '68%' : '78%',
        center: ['50%', '50%'],
        // 开启扇区标签防重叠分布，配合引线错开，减少文字拥挤。
        avoidLabelOverlap: true,
        itemStyle: { borderColor: t.bgSecondary, borderWidth: 2 },
        label: {
          show: showLabels,
          color: t.textPrimary,
          // 字号收窄至约原 70%，为引线与标签留出更多排布空间。
          fontSize: 8,
          formatter: '{b}: {c}',
        },
        labelLine: {
          show: showLabels,
          // 适当延长引线两段长度，使标签外移、纵向间距增大。
          length: 12,
          length2: 18,
          smooth: true,
          lineStyle: { color: t.borderSubtle },
        },
        // 不隐藏重叠标签（确保名称可见），并自动沿纵向错开避免文字重叠。
        labelLayout: { hideOverlap: false, moveOverlap: 'shiftY' },
        // 悬浮某扇区时：仅该扇区弹起放大，对应引线延长、文字放大；其余不变。
        emphasis: {
          scale: true,
          scaleSize: 6,
          label: {
            fontSize: 11,
            fontWeight: 600,
          },
          labelLine: {
            length: 14,
            length2: 22,
          },
        },
        data,
      },
    ],
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.donut-chart {
  width: 150px;
  height: 150px;
  flex-shrink: 0;

  // showLabels 模式：画布撑满父容器，为引线标签留足空间。
  &.is-full {
    width: 100%;
    height: 100%;
    flex: 1;
    min-height: 0;
  }
}

.donut-canvas {
  width: 100%;
  height: 100%;
}

.chart-empty {
  width: 150px;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
  font-size: $font-caption;

  &.is-full {
    width: 100%;
    height: 100%;
  }
}
</style>
