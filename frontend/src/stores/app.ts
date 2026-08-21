import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const globalLoading = ref(false)

  // ── 主题状态 ──────────────────────────────────────────────────
  const themeMode = ref<ThemeMode>((localStorage.getItem('themeMode') as ThemeMode) || 'system')
  const resolvedTheme = ref<'light' | 'dark'>('dark')

  // 系统主题偏好 MediaQuery
  let systemMedia: MediaQueryList | null = null
  let systemChangeHandler: ((e: MediaQueryListEvent) => void) | null = null

  function getSystemTheme(): 'light' | 'dark' {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light'
    }
    return 'dark'
  }

  function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
    if (mode === 'system') return getSystemTheme()
    return mode
  }

  function applyTheme(theme: 'light' | 'dark') {
    resolvedTheme.value = theme
    document.documentElement.setAttribute('data-theme', theme)
  }

  function setThemeMode(mode: ThemeMode) {
    themeMode.value = mode
    localStorage.setItem('themeMode', mode)
    applyTheme(resolveTheme(mode))
    setupSystemListener(mode)
  }

  function setupSystemListener(mode: ThemeMode) {
    // 清理旧监听
    if (systemMedia && systemChangeHandler) {
      systemMedia.removeEventListener('change', systemChangeHandler)
      systemMedia = null
      systemChangeHandler = null
    }

    if (mode === 'system' && window.matchMedia) {
      systemMedia = window.matchMedia('(prefers-color-scheme: light)')
      systemChangeHandler = (e: MediaQueryListEvent) => {
        applyTheme(e.matches ? 'light' : 'dark')
      }
      systemMedia.addEventListener('change', systemChangeHandler)
    }
  }

  function initTheme() {
    const mode = themeMode.value
    applyTheme(resolveTheme(mode))
    setupSystemListener(mode)
  }

  // 三态循环切换：light → dark → system → light。
  // 点击按钮顺序切换，下拉列表则可直接选定目标模式。
  function toggleTheme() {
    const order: ThemeMode[] = ['light', 'dark', 'system']
    const idx = order.indexOf(themeMode.value)
    const next = order[(idx + 1) % order.length]
    setThemeMode(next)
  }

  // ── 侧边栏 ──────────────────────────────────────────────────
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setGlobalLoading(loading: boolean) {
    globalLoading.value = loading
  }

  return {
    sidebarCollapsed, globalLoading,
    themeMode, resolvedTheme,
    toggleSidebar, setGlobalLoading,
    setThemeMode, initTheme, toggleTheme,
  }
})