<template>
  <span class="status-badge" :class="status">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { STATUS_MAP } from '@/utils/constants'

const props = defineProps<{ status: string }>()
const { t } = useI18n()

const label = computed(() => t(STATUS_MAP[props.status] || props.status))
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  font-size: $font-caption;
  font-weight: 500;
  border-radius: $radius-sm;
  line-height: 20px;
  white-space: nowrap;

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-right: 6px;
  }

  &.active {
    color: $active;
    background: rgba($active, 0.1);
    border: 1px solid rgba($active, 0.25);
    &::before { background: $active; }
  }
  &.draft {
    color: $info;
    background: rgba($info, 0.1);
    border: 1px solid rgba($info, 0.25);
    &::before { background: $info; }
  }
  &.disabled {
    color: $disabled;
    background: rgba($disabled, 0.1);
    border: 1px solid rgba($disabled, 0.25);
    &::before { background: $disabled; }
  }
  &.archived {
    color: $archived;
    background: rgba($archived, 0.1);
    border: 1px solid rgba($archived, 0.25);
    &::before { background: $archived; }
  }
}
</style>