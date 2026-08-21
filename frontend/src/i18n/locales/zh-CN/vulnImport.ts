// CVE 导入页（VulnImportView.vue）
export default {
  headerDesc: '支持 JSON、JSONL、YAML、Markdown，单文件限制 10MB，自动判定格式与去重合并',
  viewTemplates: '查看模板',
  continueImport: '继续导入',
  viewList: '查看 CVE 列表',
  mode: {
    file: '上传文件',
    paste: '粘贴文本',
  },
  upload: {
    title: '拖拽文件到此处',
    desc: '支持批量选择，可一次导入多个 CVE 文件',
  },
  detectUnknown: '未知格式',
  batchSummary: '已选 {count} 个文件，将依次导入并汇总结果',
  clearAll: '全部清除',
  paste: {
    placeholder: '在此粘贴 CVE 内容，支持 JSON / JSONL / YAML / Markdown，系统将自动识别',
    hint: 'JSON 支持单对象或数组；JSONL 每行一个对象；YAML 支持多文档；Markdown 取 front-matter',
  },
  import: {
    running: '正在导入...',
    action: '解析并导入',
  },
  result: {
    title: '导入结果',
    total: '总计',
    created: '新建',
    updated: '更新',
    skipped: '跳过（无变更）',
    failed: '失败',
    failDetail: '失败详情',
    unknownItem: '未知条目',
    successMsg: '成功处理 {success} 条 CVE（新建 {created} / 更新 {updated}），点击「查看 CVE 列表」浏览',
  },
  empty: {
    title: '等待导入',
    desc: '选择文件或粘贴 CVE 内容后，点击「解析并导入」开始处理',
    features: {
      auto: '自动格式识别',
      dedup: '去重合并（仅补缺）',
      batch: '批量多文件支持',
    },
  },
  template: {
    drawerTitle: '导入模板',
    copy: '复制',
    copied: '模板已复制',
  },
  format: {
    txt: '文本',
  },
}
