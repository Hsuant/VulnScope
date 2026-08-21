// vue-i18n 入口：Composition API 模式（legacy: false）。
// 默认语言：localStorage 中的用户偏好 > 浏览器语言（zh* → 简体中文，否则英文），
// 兜底回退 zh-CN（语言包不完整时保证界面不出现裸 key）。
import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

export type AppLocale = 'zh-CN' | 'en'
export const SUPPORTED_LOCALES: AppLocale[] = ['zh-CN', 'en']
export const LOCALE_STORAGE_KEY = 'appLocale'

export function getInitialLocale(): AppLocale {
  const saved = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (saved === 'zh-CN' || saved === 'en') return saved
  const lang = (navigator.language || '').toLowerCase()
  return lang.startsWith('zh') ? 'zh-CN' : 'en'
}

export function setStoredLocale(locale: AppLocale) {
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  document.documentElement.setAttribute('lang', locale === 'en' ? 'en' : 'zh-CN')
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true, // 模板中可直接使用 $t()
  locale: getInitialLocale(),
  fallbackLocale: 'zh-CN',
  fallbackWarn: false,
  missingWarn: false,
  messages: { 'zh-CN': zhCN, en: enUS },
})