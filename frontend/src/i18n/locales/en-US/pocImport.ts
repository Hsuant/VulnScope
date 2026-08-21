// POC import page (PocImportView.vue)
export default {
  headerDesc: 'Supports Nuclei, Pocsuite3, Xray, Goby templates and Markdown documents; batch multi-file, 10MB per file',
  viewTemplates: 'View Templates',
  continueImport: 'Import More',
  viewPocList: 'View POC List',
  mode: {
    file: 'Upload File',
    paste: 'Paste Text',
  },
  upload: {
    title: 'Drop files here',
    desc: 'Batch selection supported — import multiple POC files at once',
  },
  detectUnknown: 'Unknown format',
  batchSummary: '{count} files selected — they will be imported sequentially and aggregated',
  clearAll: 'Clear All',
  paste: {
    placeholder: 'Paste POC templates or Markdown content here. Multiple YAML documents separated by --- are supported.',
    hint: 'Supports Nuclei (yaml), Pocsuite3 (yaml/py), Xray (yaml/json), Goby (json/go), Markdown (md) — auto-detected',
  },
  config: {
    source: 'Source tag',
    status: 'Default status',
  },
  import: {
    running: 'Importing...',
    action: 'Parse & Import',
  },
  result: {
    title: 'Import Result',
    total: 'Total',
    success: 'Success',
    skipped: 'Skipped (deduped)',
    failed: 'Failed',
    failDetail: 'Failure details',
    unknownItem: 'Unknown item',
    successMsg: 'Imported {count} POCs — click "View POC List" to browse',
  },
  empty: {
    title: 'Awaiting import',
    desc: 'Select files or paste POC content, then click "Parse & Import"',
    features: {
      auto: 'Automatic format detection',
      dedup: 'Content deduplication',
      batch: 'Multi-template batch support',
    },
  },
  template: {
    drawerTitle: 'Import Templates',
    copy: 'Copy',
    copied: 'Template copied',
  },
  format: {
    txt: 'Text',
  },
}
