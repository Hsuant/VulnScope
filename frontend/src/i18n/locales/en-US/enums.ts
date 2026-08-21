// Enum labels: severity / status / source / format / audit actions / roles
// Mirrors the `value` fields in utils/constants.ts.
// Note: action keys use dotted paths `enums.action.poc.created`, so they are nested
// objects here (not dotted single keys) — otherwise t() path resolution fails.
export default {
  severity: {
    info: 'Info',
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    critical: 'Critical',
  },
  status: {
    draft: 'Draft',
    active: 'Active',
    disabled: 'Disabled',
    archived: 'Archived',
  },
  source: {
    manual: 'Manual',
    imported: 'Imported',
    ai: 'AI',
    crawler: 'Crawler',
  },
  format: {
    nuclei: 'Nuclei',
    json: 'JSON',
    pocsuite3: 'Pocsuite3',
    'raw-script': 'Script',
    markdown: 'Markdown',
  },
  action: {
    poc: {
      created: 'Create POC',
      updated: 'Update POC',
      deleted: 'Delete POC',
      status_changed: 'Status Change',
      version_created: 'Version Snapshot',
      batch_imported: 'Batch Import',
    },
  },
  role: {
    viewer: 'Viewer',
    editor: 'Editor',
    admin: 'Administrator',
  },
}
