import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  const canEdit = computed(() => hasRole('editor', 'admin'))
  const canAdmin = computed(() => hasRole('admin'))
  // 别名：模板与路由守卫中常用 isAdmin / isEditor 语义
  const isAdmin = canAdmin

  function hasRole(...roles: string[]): boolean {
    return roles.includes(authStore.user?.role || '')
  }

  return { hasRole, canEdit, canAdmin, isAdmin }
}
