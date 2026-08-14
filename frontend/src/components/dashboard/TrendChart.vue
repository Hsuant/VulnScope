<template>
  <div class="chart-box">
    <VChart :option="option" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '@/utils/echarts'
import { useChartTheme } from '@/composables/useChartTheme'

const props = defineProps<{
  points: { date: string; count: number }[]
}>()

const theme = useChartTheme()

function shortDate(v: string): string {
  const d = new Date(v + 'T00:00:00')
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const option = computed(() => {
  const t = theme.value
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: t.bgSecondary,
      borderColor: t.borderSubtle,
      textStyle: { color: t.textPrimary },
      formatter: (params: { axisValue: string; value: number }[]) => {
        const p = params[0]
        return `${shortDate(p.axisValue)}<br/>新增 <b>${p.value}</b>`
      },
    },
    grid: { left: 6, right: 14, top: 18, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      data: props.points.map(p => p.date),
      boundaryGap: false,
      axisLine: { lineStyle: { color: t.borderSubtle } },
      axisTick: { show: false },
      axisLabel: {
        color: t.textDisabled,
        fontSize: 10,
        formatter: (v: string) => shortDate(v),
      },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: t.textDisabled, fontSize: 10 },
      splitLine: { lineStyle: { color: t.borderSubtle, type: 'dashed' } },
    },
    series: [
      {
        type: 'line',
        data: props.points.map(p => p.count),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        lineStyle: { width: 2, color: t.colors.accent },
        itemStyle: { color: t.colors.accent },
        areaStyle: { color: t.colors.accent, opacity: 0.16 },
        emphasis: { focus: 'series' },
      },
    ],
  }
})
</script>

<style scoped lang="scss">
.chart-box {
  width: 100%;
  height: 240px;
}
</style>
