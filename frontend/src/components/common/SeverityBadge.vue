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
    background: rgba($critical, 0.2);
    border: 1px solid rgba($critical, 0.4);
  }
  &.high {
    color: #fff;
    background: rgba($high, 0.2);
    border: 1px solid rgba($high, 0.4);
  }
  &.medium {
    color: #fff;
    background: rgba($medium, 0.2);
    border: 1px solid rgba($medium, 0.4);
  }
  &.low {
    color: #fff;
    background: rgba($low, 0.2);
    border: 1px solid rgba($low, 0.4);
  }
  &.info {
    color: $text-secondary;
    background: rgba($info, 0.2);
    border: 1px solid rgba($info, 0.4);
  }
}
</style>