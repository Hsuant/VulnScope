// Plugin panel (PluginListView.vue)
export default {
  headerDesc: 'Registered plugins and their status',
  enabled: 'Enabled',
  disabled: 'Disabled',
  empty: 'No registered plugins',
  slots: {
    parser: 'Parser',
    source: 'Source',
    verifier: 'Verifier',
    exporter: 'Exporter',
    consumer: 'EventConsumer',
  },
}
