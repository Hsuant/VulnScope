// CVE import page (VulnImportView.vue)
export default {
  headerDesc: 'Supports JSON, JSONL, YAML, Markdown; 10MB per file; auto format detection and dedup merge',
  viewTemplates: 'View Templates',
  continueImport: 'Import More',
  viewList: 'View CVE List',
  mode: {
    file: 'Upload File',
    paste: 'Paste Text',
  },
  upload: {
    title: 'Drop files here',
    desc: 'Batch selection supported — import multiple CVE files at once',
  },
  detectUnknown: 'Unknown format',
  batchSummary: '{count} files selected — they will be imported sequentially and aggregated',
  clearAll: 'Clear All',
  paste: {
    placeholder: 'Paste CVE content here. Supports JSON / JSONL / YAML / Markdown — auto-detected',
    hint: 'JSON supports single object or array; JSONL one object per line; YAML multi-document; Markdown uses front-matter',
  },
  import: {
    running: 'Importing...',
    action: 'Parse & Import',
  },
  result: {
    title: 'Import Result',
    total: 'Total',
    created: 'Created',
    updated: 'Updated',
    skipped: 'Skipped (unchanged)',
    failed: 'Failed',
    failDetail: 'Failure details',
    unknownItem: 'Unknown item',
    successMsg: 'Processed {success} CVEs (created {created} / updated {updated}) — click "View CVE List" to browse',
  },
  empty: {
    title: 'Awaiting import',
    desc: 'Select files or paste CVE content, then click "Parse & Import"',
    features: {
      auto: 'Automatic format detection',
      dedup: 'Dedup merge (fill gaps only)',
      batch: 'Multi-file batch support',
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
