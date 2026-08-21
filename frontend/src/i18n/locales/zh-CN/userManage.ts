// 用户管理页（UserManageView.vue）
export default {
  createUser: '新建用户',
  editUser: '编辑用户',
  columns: {
    username: '用户名',
    email: '邮箱',
    role: '角色',
    lastLogin: '最后登录',
    createdAt: '创建时间',
  },
  fields: {
    username: '用户名',
    email: '邮箱',
    password: '密码',
    role: '角色',
    active: '启用',
  },
  placeholders: {
    username: '3-64 字符，字母数字下划线',
    emailOptional: '可选',
    passwordEdit: '留空则不修改',
    passwordNew: '至少 8 位',
  },
  rules: {
    usernameRequired: '请输入用户名',
    usernamePattern: '3-64 字符，仅允许字母数字下划线连字符',
    passwordRequired: '请输入密码',
    passwordMin: '密码至少 8 位',
  },
  messages: {
    updateSuccess: '用户更新成功',
    createSuccess: '用户创建成功',
    deleteSuccess: '用户已删除',
  },
}
