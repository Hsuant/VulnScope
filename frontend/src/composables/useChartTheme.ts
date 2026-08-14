// 读取运行时 CSS 自定义属性，为 ECharts 提供随主题切换的颜色。
// 图表颜色无法直接用 var()，因此在此解析为具体色值；
// resolvedTheme 变化时（用户切换主题）在下一帧重新读取并触发图表 option 重算。

import { ref, watch, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'

export type ChartColorKey =
  | 'accent' | 'active' | 'high' | 'medium' | 'low' | 'info'
  | 'critical' | 'disabled' | 'archived'

export interface ChartTheme {
  colors: Record<ChartColorKey, string>
  textPrimary: string
  textSecondary: string
  textDisabled: string
  borderSubtle: string
  bgSecondary: string
  bgTertiary: string
}

function read(): ChartTheme {
  const s = getComputedStyle(document.documentElement)
  const g = (n: string) => s.getPropertyValue(n).trim()
  return {
    colors: {
      accent: g('--vs-accent'),
      active: g('--vs-active'),
      high: g('--vs-high'),
      medium: g('--vs-medium'),
      low: g('--vs-low'),
      info: g('--vs-info'),
      critical: g('--vs-critical'),
      disabled: g('--vs-disabled'),
      archived: g('--vs-archived'),
    },
    textPrimary: g('--vs-text-primary'),
    textSecondary: g('--vs-text-secondary'),
    textDisabled: g('--vs-text-disabled'),
    borderSubtle: g('--vs-border-subtle'),
    bgSecondary: g('--vs-bg-secondary'),
    bgTertiary: g('--vs-bg-tertiary'),
  }
}

export function useChartTheme() {
  const theme = ref<ChartTheme>(read())
  const app = useAppStore()
  watch(
    () => app.resolvedTheme,
    () => {
      // 主题属性已写入 <html>，下一帧再读取保证取到新值
      requestAnimationFrame(() => {
        theme.value = read()
      })
    },
  )
  onMounted(() => {
    theme.value = read()
  })
  return theme
}

/** 将颜色键解析为 CSS 变量引用（用于 HTML 图例圆点，随主题自动切换） */
export function cssVar(key: ChartColorKey | string): string {
  return `var(--vs-${key})`
}
