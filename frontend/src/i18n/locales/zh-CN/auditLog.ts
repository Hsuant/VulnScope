// 审计日志页（AuditLogView.vue）
export default {
  headerDesc: '所有写操作的全量审计记录',
  detailTitle: '审计详情',
  before: 'before',
  after: 'after',
  resourceUser: '用户',
  resourceTag: '标签',
  filters: {
    action: '操作类型',
    resourceType: '资源类型',
    userId: '用户 ID',
  },
  columns: {
    time: '时间',
    user: '用户',
    action: '操作',
    resource: '资源',
    resourceId: '资源 ID',
    detail: '详情',
  },
}
