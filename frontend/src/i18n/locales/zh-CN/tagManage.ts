// 标签管理页（TagManageView.vue）
export default {
  createTag: '新建标签',
  editTag: '编辑标签',
  searchPlaceholder: '搜索标签名称或命名空间...',
  noMatch: '无匹配标签',
  noTags: '暂无标签',
  tryOtherKeywords: '尝试其他搜索关键词',
  noneCreated: '尚未创建任何标签',
  columns: {
    color: '颜色',
    pocCount: 'POC 数',
  },
  fields: {
    namespace: '命名空间',
    tagName: '标签名',
    color: '颜色',
    description: '描述',
  },
  placeholders: {
    namespace: '选择或输入命名空间',
    tagName: '标签名称',
    description: '描述信息',
  },
  rules: {
    namespace: '请输入命名空间',
    tagName: '请输入标签名',
  },
  messages: {
    createSuccess: '标签创建成功',
    updateSuccess: '标签更新成功',
    deleteSuccess: '标签已删除',
  },
}
