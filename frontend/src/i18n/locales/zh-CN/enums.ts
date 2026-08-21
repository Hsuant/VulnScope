// 枚举标签：严重级别 / 状态 / 来源 / 格式 / 审计动作 / 角色
// 与 utils/constants.ts 中的 value 逐一对应，供列表、表单与徽章展示。
// 注意：action 键为 `enums.action.poc.created` 形式（点分路径），故此处用嵌套对象，
// 而非带点的单键——否则 t('enums.action.poc.created') 会按路径解析失败。
export default {
  severity: {
    info: '信息',
    low: '低危',
    medium: '中危',
    high: '高危',
    critical: '严重',
  },
  status: {
    draft: '草稿',
    active: '已启用',
    disabled: '已禁用',
    archived: '已归档',
  },
  source: {
    manual: '手动录入',
    imported: '导入',
    ai: 'AI 生成',
    crawler: '爬取',
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
      created: '创建 POC',
      updated: '更新 POC',
      deleted: '删除 POC',
      status_changed: '状态变更',
      version_created: '版本快照',
      batch_imported: '批量导入',
    },
  },
  role: {
    viewer: '查看者',
    editor: '编辑者',
    admin: '管理员',
  },
}
