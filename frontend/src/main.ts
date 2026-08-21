import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import { useAppStore } from '@/stores/app'
import { i18n } from '@/i18n'
import './styles/global.scss'

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

const pinia = createPinia()
app.use(pinia)

// 挂载前应用主题：避免首帧闪现默认深色后再切到用户偏好（如浅色）
useAppStore().initTheme()

app.use(router)
app.use(ElementPlus, { size: 'default' })
app.use(i18n)
app.mount('#app')