// ECharts 按需注册：仅引入 Dashboard 所用图表与组件，控制打包体积。
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, LineChart, HeatmapChart } from 'echarts/charts'
import {
  TooltipComponent,
  GridComponent,
  TitleComponent,
  AxisPointerComponent,
  VisualMapComponent,
} from 'echarts/components'
import { LegacyGridContainLabel } from 'echarts/features'

use([
  CanvasRenderer,
  PieChart,
  BarChart,
  LineChart,
  HeatmapChart,
  TooltipComponent,
  GridComponent,
  TitleComponent,
  AxisPointerComponent,
  // 热力图需 VisualMap 组件将数值映射为色阶。
  VisualMapComponent,
  // ECharts 6 将 grid.containLabel 迁移为 legacy 特性，需显式注册，
  // 否则坐标轴标签可能因网格未扩展而被裁切。
  LegacyGridContainLabel,
])
