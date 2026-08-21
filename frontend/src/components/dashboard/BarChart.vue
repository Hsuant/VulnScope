<template>
  <div class="chart-box">
    <VChart v-if="items.length" :option="option" autoresize />
    <div v-else class="chart-empty">{{ $t('dashboard.charts.noData') }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '@/utils/echarts'
import { useChartTheme, type ChartColorKey } from '@/composables/useChartTheme'

export interface BarItem {
  name: string
  value: number
  colorKey: ChartColorKey
}

const props = defineProps<{
  items: BarItem[]
  horizontal?: boolean
}>()

const theme = useChartTheme()

const option = computed(() => {
  const t = theme.value
  const horizontal = !!props.horizontal
  const names = props.items.map(i => i.name)
  const data = props.items.map(i => ({
    value: i.value,
    itemStyle: {
      color: t.colors[i.colorKey] || t.colors.accent,
      borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
    },
  }))
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: t.bgSecondary,
      borderColor: t.borderSubtle,
      textStyle: { color: t.textPrimary },
    },
    grid: {
      left: horizontal ? 10 : 20,
      right: 16,
      top: 18,
      bottom: horizontal ? 6 : 24,
      containLabel: true,
    },
    xAxis: horizontal
      ? {
          type: 'value',
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: t.textDisabled, fontSize: 11 },
          splitLine: { lineStyle: { color: t.borderSubtle, type: 'dashed' } },
        }
      : {
          type: 'category',
          data: names,
          axisLine: { lineStyle: { color: t.borderSubtle } },
          axisTick: { show: false },
          axisLabel: { color: t.textSecondary, fontSize: 11, interval: 0 },
        },
    yAxis: horizontal
      ? {
          type: 'category',
          data: names,
          inverse: true,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: t.textSecondary,
            fontSize: 11,
            width: 90,
            overflow: 'truncate',
          },
        }
      : {
          type: 'value',
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: t.textDisabled, fontSize: 11 },
          splitLine: { lineStyle: { color: t.borderSubtle, type: 'dashed' } },
        },
    series: [
      {
        type: 'bar',
        data,
        barWidth: horizontal ? '58%' : '46%',
        label: {
          show: true,
          position: horizontal ? 'right' : 'top',
          color: t.textSecondary,
          fontSize: 11,
          formatter: '{c}',
        },
      },
    ],
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.chart-box {
  width: 100%;
  height: 220px;
}

.chart-empty {
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
  font-size: $font-caption;
}
</style>
