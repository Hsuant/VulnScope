// CVE list page (VulnListView.vue)
export default {
  headerDesc: 'Display and maintain CVE data — search, filter, delete and batch delete',
  searchPlaceholder: 'Search CVE ID or title...',
  severityPlaceholder: 'Severity',
  columns: {
    cveId: 'CVE ID',
    pocCount: 'POCs',
  },
  deleteConfirm: 'Delete CVE {cve}? This cannot be undone.',
  deleteBatchConfirm: 'Delete the {count} selected CVEs? This cannot be undone.',
  exportTitle: 'Export CVEs',
  exportMessage: 'Choose an export format:',
  exportJson: 'JSON (full fields, re-importable)',
  exportYaml: 'YAML',
  selectExportItems: 'Please select CVEs to export first',
  exportSuccess: 'Exported successfully',
}
