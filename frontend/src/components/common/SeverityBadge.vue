<template>
  <span class="severity-badge" :class="severity">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SEVERITY_MAP } from '@/utils/constants'

const props = defineProps<{ severity: string }>()

const label = computed(() => SEVERITY_MAP[props.severity] || props.severity)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.severity-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  font-size: $font-caption;
  font-weight: 500;
  border-radius: $radius-sm;
  line-height: 20px;
  white-space: nowrap;

  &.critical {
    color: #fff;
    background: rgba(var(--vs-critical-rgb), 0.2);
    border: 1px solid rgba(var(--vs-critical-rgb), 0.4);
  }
  &.high {
    color: #fff;
    background: rgba(var(--vs-high-rgb), 0.2);
    border: 1px solid rgba(var(--vs-high-rgb), 0.4);
  }
  &.medium {
    color: #fff;
    background: rgba(var(--vs-medium-rgb), 0.2);
    border: 1px solid rgba(var(--vs-medium-rgb), 0.4);
  }
  &.low {
    color: #fff;
    background: rgba(var(--vs-low-rgb), 0.2);
    border: 1px solid rgba(var(--vs-low-rgb), 0.4);
  }
  &.info {
    color: $text-secondary;
    background: rgba(var(--vs-info-rgb), 0.2);
    border: 1px solid rgba(var(--vs-info-rgb), 0.4);
  }
}
</style>