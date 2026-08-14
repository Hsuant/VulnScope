import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

service.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.accessToken) {
    config.headers.Authorization = `Bearer ${authStore.accessToken}`
  }
  return config
})

service.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data
    if (code !== 'OK') {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message))
    }
    return data
  },
  async (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      if (authStore.refreshToken) {
        try {
          await authStore.refreshTokenAction()
          const config = error.config
          config.headers.Authorization = `Bearer ${authStore.accessToken}`
          return service(config)
        } catch {
          authStore.logout()
        }
      } else {
        authStore.logout()
      }
    }
    const msg = error.response?.data?.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default service