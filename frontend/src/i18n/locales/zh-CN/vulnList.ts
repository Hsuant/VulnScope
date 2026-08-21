// CVE 列表页（VulnListView.vue）
export default {
  headerDesc: 'CVE 漏洞数据展示与维护，支持搜索、筛选、删除与批量删除',
  searchPlaceholder: '搜索 CVE 编号或标题...',
  severityPlaceholder: '严重级别',
  columns: {
    cveId: 'CVE 编号',
    pocCount: 'POC 数',
  },
  deleteConfirm: '确定要删除 CVE {cve} 吗？此操作不可恢复。',
  deleteBatchConfirm: '确定要删除选中的 {count} 个 CVE 吗？此操作不可恢复。',
  exportTitle: '导出 CVE',
  exportMessage: '选择导出格式：',
  exportJson: 'JSON（包含完整字段，可再导入）',
  exportYaml: 'YAML',
  selectExportItems: '请先选择要导出的 CVE',
  exportSuccess: '导出成功',
}
