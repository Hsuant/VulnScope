import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, refresh as apiRefresh, getMe } from '@/api/auth'
import type { UserInfo } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))
  const refreshToken = ref<string | null>(localStorage.getItem('refreshToken'))
  const user = ref<UserInfo | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const userRole = computed(() => user.value?.role || '')
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEditor = computed(() => user.value?.role === 'editor' || user.value?.role === 'admin')
  const isViewer = computed(() => user.value?.role === 'viewer')

  async function login(username: string, password: string) {
    const res = await apiLogin({ username, password })
    accessToken.value = res.access_token
    refreshToken.value = res.refresh_token
    user.value = res.user
    localStorage.setItem('accessToken', res.access_token)
    localStorage.setItem('refreshToken', res.refresh_token)
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  async function refreshTokenAction() {
    if (!refreshToken.value) throw new Error('No refresh token')
    const res = await apiRefresh(refreshToken.value)
    accessToken.value = res.access_token
    refreshToken.value = res.refresh_token
    localStorage.setItem('accessToken', res.access_token)
    localStorage.setItem('refreshToken', res.refresh_token)
  }

  async function fetchCurrentUser() {
    const u = await getMe()
    user.value = u
  }

  return {
    accessToken, refreshToken, user,
    isAuthenticated, userRole, isAdmin, isEditor, isViewer,
    login, logout, refreshTokenAction, fetchCurrentUser,
  }
})