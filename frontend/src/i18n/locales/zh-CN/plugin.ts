// 插件面板（PluginListView.vue）
export default {
  headerDesc: '已注册的插件列表及运行状态',
  enabled: '已启用',
  disabled: '已禁用',
  empty: '暂无注册插件',
  slots: {
    parser: 'Parser 解析器',
    source: 'Source 来源',
    verifier: 'Verifier 验证引擎',
    exporter: 'Exporter 导出器',
    consumer: 'EventConsumer 事件消费者',
  },
}
