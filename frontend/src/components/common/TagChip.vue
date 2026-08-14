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
  const color = props.tag.color || '#4a8cba'
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