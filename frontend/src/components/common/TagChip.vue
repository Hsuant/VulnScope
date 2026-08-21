<template>
  <span class="tag-chip" :style="chipStyle">
    {{ tag.name }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  tag: { name: string; namespace?: string; color?: string | null }
  closable?: boolean
}>()

const chipStyle = computed(() => {
  const color = props.tag.color
  // 无自定义颜色时回退到主题强调色（随浅/暗主题自动切换，无法用十六进制追加 alpha，
  // 改用 color-mix 生成低透明度背景与边框）。
  if (!color) {
    return {
      background: 'color-mix(in srgb, var(--vs-accent) 12%, transparent)',
      border: '1px solid color-mix(in srgb, var(--vs-accent) 25%, transparent)',
      color: 'var(--vs-accent)',
    }
  }
  return {
    background: `${color}18`,
    border: `1px solid ${color}30`,
    color,
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.tag-chip {
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  font-size: $font-caption;
  line-height: 22px;
  border-radius: $radius-sm;
  white-space: nowrap;
  cursor: default;
}
</style>