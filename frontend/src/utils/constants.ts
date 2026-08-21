// 枚举常量：值清单保持不变，展示标签一律改为 i18n key（对应 i18n/locales/*/enums.ts），
// 由组件在渲染时通过 t($t) 翻译，随语言切换即时更新。

export const SEVERITY_MAP: Record<string, string> = {
  info: 'enums.severity.info',
  low: 'enums.severity.low',
  medium: 'enums.severity.medium',
  high: 'enums.severity.high',
  critical: 'enums.severity.critical',
}

export const STATUS_MAP: Record<string, string> = {
  draft: 'enums.status.draft',
  active: 'enums.status.active',
  disabled: 'enums.status.disabled',
  archived: 'enums.status.archived',
}

export const SOURCE_MAP: Record<string, string> = {
  manual: 'enums.source.manual',
  imported: 'enums.source.imported',
  ai: 'enums.source.ai',
  crawler: 'enums.source.crawler',
}

export const FORMAT_MAP: Record<string, string> = {
  'nuclei': 'enums.format.nuclei',
  json: 'enums.format.json',
  pocsuite3: 'enums.format.pocsuite3',
  'raw-script': 'enums.format.raw-script',
  markdown: 'enums.format.markdown',
}

export const ACTION_MAP: Record<string, string> = {
  'poc.created': 'enums.action.poc.created',
  'poc.updated': 'enums.action.poc.updated',
  'poc.deleted': 'enums.action.poc.deleted',
  'poc.status_changed': 'enums.action.poc.status_changed',
  'poc.version_created': 'enums.action.poc.version_created',
  'poc.batch_imported': 'enums.action.poc.batch_imported',
}

export const ROLE_MAP: Record<string, string> = {
  viewer: 'enums.role.viewer',
  editor: 'enums.role.editor',
  admin: 'enums.role.admin',
}

export const SEVERITY_ORDER: Record<string, number> = {
  info: 0, low: 1, medium: 2, high: 3, critical: 4,
}

export const SEVERITY_OPTIONS = [
  { value: 'info', label: 'enums.severity.info' },
  { value: 'low', label: 'enums.severity.low' },
  { value: 'medium', label: 'enums.severity.medium' },
  { value: 'high', label: 'enums.severity.high' },
  { value: 'critical', label: 'enums.severity.critical' },
]

export const STATUS_OPTIONS = [
  { value: 'draft', label: 'enums.status.draft' },
  { value: 'active', label: 'enums.status.active' },
  { value: 'disabled', label: 'enums.status.disabled' },
  { value: 'archived', label: 'enums.status.archived' },
]

export const SOURCE_OPTIONS = [
  { value: 'manual', label: 'enums.source.manual' },
  { value: 'imported', label: 'enums.source.imported' },
  { value: 'ai', label: 'enums.source.ai' },
  { value: 'crawler', label: 'enums.source.crawler' },
]

export const FORMAT_OPTIONS = [
  { value: 'nuclei', label: 'enums.format.nuclei' },
  { value: 'pocsuite3', label: 'enums.format.pocsuite3' },
  { value: 'json', label: 'enums.format.json' },
  { value: 'raw-script', label: 'enums.format.raw-script' },
  { value: 'markdown', label: 'enums.format.markdown' },
]

export const STATUS_TRANSITIONS: Record<string, string[]> = {
  draft: ['active', 'disabled'],
  active: ['disabled', 'archived'],
  disabled: ['active', 'archived'],
  archived: ['active'],
}