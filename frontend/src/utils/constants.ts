export const SEVERITY_MAP: Record<string, string> = {
  info: '信息',
  low: '低危',
  medium: '中危',
  high: '高危',
  critical: '严重',
}

export const STATUS_MAP: Record<string, string> = {
  draft: '草稿',
  active: '已启用',
  disabled: '已禁用',
  archived: '已归档',
}

export const SOURCE_MAP: Record<string, string> = {
  manual: '手动录入',
  imported: '导入',
  ai: 'AI 生成',
  crawler: '爬取',
}

export const FORMAT_MAP: Record<string, string> = {
  'nuclei-yaml': 'Nuclei',
  json: 'JSON',
  pocsuite3: 'Pocsuite3',
  'raw-script': '原始脚本',
}

export const ACTION_MAP: Record<string, string> = {
  'poc.created': '创建 POC',
  'poc.updated': '更新 POC',
  'poc.deleted': '删除 POC',
  'poc.status_changed': '状态变更',
  'poc.version_created': '版本快照',
  'poc.batch_imported': '批量导入',
}

export const SEVERITY_COLORS: Record<string, string> = {
  critical: '#c43e3e',
  high: '#c47a3e',
  medium: '#c4a63e',
  low: '#3e7ec4',
  info: '#6a6a72',
}

export const STATUS_COLORS: Record<string, string> = {
  active: '#3ea85e',
  draft: '#6a6a72',
  disabled: '#c43e3e',
  archived: '#7e5ec4',
}

export const SEVERITY_ORDER: Record<string, number> = {
  info: 0, low: 1, medium: 2, high: 3, critical: 4,
}

export const SEVERITY_OPTIONS = [
  { value: 'info', label: '信息' },
  { value: 'low', label: '低危' },
  { value: 'medium', label: '中危' },
  { value: 'high', label: '高危' },
  { value: 'critical', label: '严重' },
]

export const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '已启用' },
  { value: 'disabled', label: '已禁用' },
  { value: 'archived', label: '已归档' },
]

export const SOURCE_OPTIONS = [
  { value: 'manual', label: '手动录入' },
  { value: 'imported', label: '导入' },
  { value: 'ai', label: 'AI 生成' },
  { value: 'crawler', label: '爬取' },
]

export const FORMAT_OPTIONS = [
  { value: 'nuclei-yaml', label: 'Nuclei' },
  { value: 'pocsuite3', label: 'Pocsuite3' },
  { value: 'json', label: 'JSON' },
  { value: 'raw-script', label: '原始脚本' },
]

export const STATUS_TRANSITIONS: Record<string, string[]> = {
  draft: ['active', 'disabled'],
  active: ['disabled', 'archived'],
  disabled: ['active', 'archived'],
  archived: ['active'],
}