<template>
  <el-config-provider :locale="epLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

// 主题初始化在 main.ts 中（挂载前）执行，避免首帧主题闪烁。
const { locale } = useI18n()

// Element Plus 组件内置文案随界面语言切换
const epLocale = computed(() => (locale.value === 'en' ? en : zhCn))
</script>