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
        meta: { title: 'nav.dashboard', icon: 'Grid' },
      },
      {
        path: 'pocs',
        name: 'PocList',
        component: () => import('@/views/poc/PocListView.vue'),
        meta: { title: 'nav.pocList', icon: 'Document' },
      },
      {
        path: 'pocs/new',
        name: 'PocCreate',
        component: () => import('@/views/poc/PocFormView.vue'),
        meta: { title: 'nav.pocCreate', icon: 'Edit', roles: ['editor', 'admin'] },
      },
      {
        path: 'pocs/:id',
        name: 'PocDetail',
        component: () => import('@/views/poc/PocDetailView.vue'),
        meta: { title: 'nav.pocDetail' },
      },
      {
        path: 'pocs/:id/edit',
        name: 'PocEdit',
        component: () => import('@/views/poc/PocFormView.vue'),
        meta: { title: 'nav.pocEdit', roles: ['editor', 'admin'] },
      },
      {
        path: 'pocs/import',
        name: 'PocImport',
        component: () => import('@/views/poc/PocImportView.vue'),
        meta: { title: 'nav.pocImport', icon: 'Upload', roles: ['editor', 'admin'] },
      },
      {
        path: 'tags',
        name: 'TagManage',
        component: () => import('@/views/tags/TagManageView.vue'),
        meta: { title: 'nav.tagManage', icon: 'Collection' },
      },
      {
        path: 'vulns',
        name: 'VulnList',
        component: () => import('@/views/vulns/VulnListView.vue'),
        meta: { title: 'nav.vulnList', icon: 'Warning' },
      },
      {
        path: 'vulns/:id',
        name: 'VulnDetail',
        component: () => import('@/views/vulns/VulnDetailView.vue'),
        meta: { title: 'nav.vulnDetail' },
      },
      {
        path: 'vulns/:id/edit',
        name: 'VulnEdit',
        component: () => import('@/views/vulns/VulnFormView.vue'),
        meta: { title: 'nav.vulnEdit', roles: ['editor', 'admin'] },
      },
      {
        path: 'vulns/new',
        name: 'VulnCreate',
        component: () => import('@/views/vulns/VulnFormView.vue'),
        meta: { title: 'nav.vulnCreate', icon: 'Edit', roles: ['editor', 'admin'] },
      },
      {
        path: 'vulns/import',
        name: 'VulnImport',
        component: () => import('@/views/vulns/VulnImportView.vue'),
        meta: { title: 'nav.vulnImport', icon: 'Upload', roles: ['editor', 'admin'] },
      },
      {
        path: 'plugins',
        name: 'PluginList',
        component: () => import('@/views/plugins/PluginListView.vue'),
        meta: { title: 'nav.pluginPanel', icon: 'Setting' },
      },
      {
        path: 'system/users',
        name: 'UserManage',
        component: () => import('@/views/system/UserManageView.vue'),
        meta: { title: 'nav.userManage', icon: 'User', roles: ['admin'] },
      },
      {
        path: 'system/audit-logs',
        name: 'AuditLog',
        component: () => import('@/views/system/AuditLogView.vue'),
        meta: { title: 'nav.auditLog', icon: 'List', roles: ['admin'] },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/system/ProfileView.vue'),
        meta: { title: 'nav.profile', icon: 'User' },
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