<template>
  <div class="chart-box">
    <VChart v-if="items.length" :option="option" autoresize />
    <div v-else class="chart-empty">暂无数据</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '@/utils/echarts'
import { useChartTheme } from '@/composables/useChartTheme'

export interface TreemapItem {
  name: string
  value: number
  severity?: string
}

const props = defineProps<{
  items: TreemapItem[]
}>()

const theme = useChartTheme()

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#c43e3e',
  high: '#c47a3e',
  medium: '#c4a63e',
  low: '#3e7ec4',
  info: '#6a6a72',
}

const option = computed(() => {
  const t = theme.value
  const data = props.items.map(i => ({
    name: i.name,
    value: i.value,
    itemStyle: {
      color: i.severity ? (SEVERITY_COLORS[i.severity] || t.colors.accent) : t.colors.accent,
    },
  }))

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: t.bgSecondary,
      borderColor: t.borderSubtle,
      textStyle: { color: t.textPrimary },
      formatter: (params: { name: string; value: number }) =>
        `<b>${params.name}</b><br/>关联 POC: ${params.value}`,
    },
    series: [
      {
        type: 'treemap',
        data,
        roam: false,
        width: '100%',
        height: '100%',
        label: {
          show: true,
          formatter: (params: { name: string }) => params.name,
          color: '#fff',
          fontSize: 11,
          fontWeight: 500,
          textShadowColor: 'rgba(0,0,0,0.4)',
          textShadowBlur: 3,
        },
        itemStyle: {
          borderColor: t.bgSecondary,
          borderWidth: 3,
          borderRadius: 6,
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
  height: 240px;
}

.chart-empty {
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
  font-size: $font-caption;
}
</style>