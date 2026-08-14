import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { requiresAuth: false, layout: 'auth' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '工作台', icon: 'Grid' },
      },
      {
        path: 'pocs',
        name: 'PocList',
        component: () => import('@/views/poc/PocListView.vue'),
        meta: { title: 'POC 列表', icon: 'Document' },
      },
      {
        path: 'pocs/new',
        name: 'PocCreate',
        component: () => import('@/views/poc/PocFormView.vue'),
        meta: { title: '新建 POC', icon: 'Edit', roles: ['editor', 'admin'] },
      },
      {
        path: 'pocs/:id',
        name: 'PocDetail',
        component: () => import('@/views/poc/PocDetailView.vue'),
        meta: { title: 'POC 详情' },
      },
      {
        path: 'pocs/:id/edit',
        name: 'PocEdit',
        component: () => import('@/views/poc/PocFormView.vue'),
        meta: { title: '编辑 POC', roles: ['editor', 'admin'] },
      },
      {
        path: 'pocs/import',
        name: 'PocImport',
        component: () => import('@/views/poc/PocImportView.vue'),
        meta: { title: '导入 POC', icon: 'Upload', roles: ['editor', 'admin'] },
      },
      {
        path: 'tags',
        name: 'TagManage',
        component: () => import('@/views/tags/TagManageView.vue'),
        meta: { title: '标签管理', icon: 'Collection' },
      },
      {
        path: 'vulns',
        name: 'VulnList',
        component: () => import('@/views/vulns/VulnListView.vue'),
        meta: { title: 'CVE 漏洞库', icon: 'Warning' },
      },
      {
        path: 'plugins',
        name: 'PluginList',
        component: () => import('@/views/plugins/PluginListView.vue'),
        meta: { title: '插件面板', icon: 'Setting' },
      },
      {
        path: 'system/users',
        name: 'UserManage',
        component: () => import('@/views/system/UserManageView.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] },
      },
      {
        path: 'system/audit-logs',
        name: 'AuditLog',
        component: () => import('@/views/system/AuditLogView.vue'),
        meta: { title: '审计日志', icon: 'List', roles: ['admin'] },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/system/ProfileView.vue'),
        meta: { title: '个人信息', icon: 'User' },
      },
    ],
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/ForbiddenView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  if (to.name === 'Login' && authStore.isAuthenticated) {
    return next({ name: 'Dashboard' })
  }

  const requiredRoles = to.meta.roles as string[] | undefined
  if (requiredRoles && !requiredRoles.includes(authStore.user?.role || '')) {
    return next({ name: 'Forbidden' })
  }

  next()
})

export default router