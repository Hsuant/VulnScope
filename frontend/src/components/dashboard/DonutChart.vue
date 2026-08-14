<template>
  <div class="donut-chart">
    <VChart v-if="items.length" class="donut-canvas" :option="option" autoresize />
    <div v-else class="chart-empty">暂无数据</div>
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
}>()

const theme = useChartTheme()
const sum = computed(() => props.items.reduce((s, i) => s + i.value, 0))

const option = computed(() => {
  const t = theme.value
  const isDonut = props.variant !== 'pie'
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
        radius: isDonut ? ['62%', '82%'] : '78%',
        center: ['50%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderColor: t.bgSecondary, borderWidth: 2 },
        label: { show: false },
        labelLine: { show: false },
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
}
</style>
