// POC 导入页（PocImportView.vue）
export default {
  headerDesc: '支持 Nuclei、Pocsuite3、Xray、Goby 模板及 Markdown 文档，支持批量多文件，单文件限制 10MB',
  viewTemplates: '查看模板',
  continueImport: '继续导入',
  viewPocList: '查看 POC 列表',
  mode: {
    file: '上传文件',
    paste: '粘贴文本',
  },
  upload: {
    title: '拖拽文件到此处',
    desc: '支持批量选择，可一次导入多个 POC 文件',
  },
  detectUnknown: '未知格式',
  batchSummary: '已选 {count} 个文件，将依次导入并汇总结果',
  clearAll: '全部清除',
  paste: {
    placeholder: '在此粘贴 POC 模板或 Markdown 文档内容，支持多模板同时导入（多个 YAML 文档用 --- 分隔）',
    hint: '支持 Nuclei（yaml）、Pocsuite3（yaml/py）、Xray（yaml/json）、Goby（json/go）、Markdown（md）格式，系统将自动识别',
  },
  config: {
    source: '来源标记',
    status: '默认状态',
  },
  import: {
    running: '正在导入...',
    action: '解析并导入',
  },
  result: {
    title: '导入结果',
    total: '总计',
    success: '成功',
    skipped: '跳过（去重）',
    failed: '失败',
    failDetail: '失败详情',
    unknownItem: '未知条目',
    successMsg: '成功导入 {count} 个 POC，点击「查看 POC 列表」浏览',
  },
  empty: {
    title: '等待导入',
    desc: '选择文件或粘贴 POC 内容后，点击「解析并导入」开始处理',
    features: {
      auto: '自动格式识别',
      dedup: '内容去重检测',
      batch: '批量多模板支持',
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
