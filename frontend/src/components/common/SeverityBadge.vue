<template>
  <span class="severity-badge" :class="severity">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { SEVERITY_MAP } from '@/utils/constants'

const props = defineProps<{ severity: string }>()
const { t } = useI18n()

const label = computed(() => t(SEVERITY_MAP[props.severity] || props.severity))
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
    color: var(--vs-critical-text);
    background: var(--vs-critical-bg);
    border: 1px solid var(--vs-critical-border);
  }
  &.high {
    color: var(--vs-high-text);
    background: var(--vs-high-bg);
    border: 1px solid var(--vs-high-border);
  }
  &.medium {
    color: var(--vs-medium-text);
    background: var(--vs-medium-bg);
    border: 1px solid var(--vs-medium-border);
  }
  &.low {
    color: var(--vs-low-text);
    background: var(--vs-low-bg);
    border: 1px solid var(--vs-low-border);
  }
  &.info {
    color: var(--vs-text-secondary);
    background: var(--vs-info-bg);
    border: 1px solid var(--vs-info-border);
  }
}
</style>