<template>
  <!--
    POC 创建趋势 + CVE 趋势 双折线图：
    每日新增 POC 数与新增 CVE 数对比，覆盖最近 N 天（缺失日期补 0）。
    双轴共享 X 轴（日期），POC 用强调色、CVE 用 critical 色区分。
  -->
  <div class="chart-box">
    <VChart :option="option" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '@/utils/echarts'
import { useChartTheme } from '@/composables/useChartTheme'
import type { TrendPoint } from '@/types/dashboard'

const props = defineProps<{
  /** 每日新增 POC / CVE 趋势数据点。 */
  points: TrendPoint[]
}>()

const theme = useChartTheme()

/** 将 YYYY-MM-DD 缩写为 月/日，用于坐标轴与提示框展示。 */
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
      textStyle: { color: t.textPrimary, fontSize: 12 },
      // 同一日期下并列展示 POC / CVE 两项
      formatter: (params: { axisValue: string; seriesName: string; value: number; color: string }[]) => {
        const head = shortDate(params[0]?.axisValue ?? '')
        const rows = params
          .map((p) =>
            `<div style="display:flex;align-items:center;gap:6px;margin-top:2px">
               <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
               <span style="color:${t.textSecondary}">${p.seriesName}</span>
               <b style="margin-left:auto">${p.value}</b>
             </div>`,
          )
          .join('')
        return `<div style="font-weight:600;margin-bottom:2px">${head}</div>${rows}`
      },
    },
    // 顶部图例：POC / CVE 双系列
    legend: {
      data: ['新增 POC', '新增 CVE'],
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: t.textSecondary, fontSize: 11 },
    },
    grid: { left: 6, right: 14, top: 24, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      data: props.points.map((p) => p.date),
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
        name: '新增 POC',
        type: 'line',
        data: props.points.map((p) => p.new_pocs),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        lineStyle: { width: 2, color: t.colors.accent },
        itemStyle: { color: t.colors.accent },
        areaStyle: { color: t.colors.accent, opacity: 0.14 },
        emphasis: { focus: 'series' },
      },
      {
        name: '新增 CVE',
        type: 'line',
        data: props.points.map((p) => p.new_vulns),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        lineStyle: { width: 2, color: t.colors.critical },
        itemStyle: { color: t.colors.critical },
        areaStyle: { color: t.colors.critical, opacity: 0.10 },
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
