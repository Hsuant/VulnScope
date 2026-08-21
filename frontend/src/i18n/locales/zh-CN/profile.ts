// 个人信息页（ProfileView.vue）
export default {
  headerDesc: '查看和修改个人账号信息',
  editProfile: '编辑资料',
  accountInfo: '账号信息',
  accountStatus: '账号状态',
  changePassword: '密码修改',
  usernameReadonly: '用户名不可修改',
  passwordHint: '至少 8 位字符',
  saving: '保存中...',
  saveChanges: '保存修改',
  active: '正常',
  disabled: '已停用',
  lastLogin: '登录时间',
  registeredAt: '注册时间',
  fields: {
    username: '用户名',
    email: '邮箱',
    newPassword: '新密码',
    confirmPassword: '确认密码',
    role: '角色',
  },
  placeholders: {
    email: '请输入邮箱地址',
    newPassword: '留空则不修改密码',
    confirmPassword: '再次输入新密码',
  },
  rules: {
    email: '请输入有效的邮箱地址',
    passwordMin: '密码至少 8 位',
    passwordMismatch: '两次输入的密码不一致',
  },
  messages: {
    noChanges: '没有需要修改的内容',
    updated: '个人信息已更新',
  },
}
