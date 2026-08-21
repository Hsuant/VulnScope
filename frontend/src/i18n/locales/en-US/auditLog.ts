// Audit log page (AuditLogView.vue)
export default {
  headerDesc: 'Full audit trail of all write operations',
  detailTitle: 'Audit Detail',
  before: 'before',
  after: 'after',
  resourceUser: 'User',
  resourceTag: 'Tag',
  filters: {
    action: 'Action type',
    resourceType: 'Resource type',
    userId: 'User ID',
  },
  columns: {
    time: 'Time',
    user: 'User',
    action: 'Action',
    resource: 'Resource',
    resourceId: 'Resource ID',
    detail: 'Detail',
  },
}
