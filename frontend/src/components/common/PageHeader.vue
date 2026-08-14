<template>
  <div class="page-header">
    <div class="header-left">
      <h1 class="header-title">{{ title }}</h1>
      <p v-if="description" class="header-desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.header-title {
  font-size: 20px;
  font-weight: 600;
  color: $text-primary;
  line-height: 1.3;
  margin: 0;
}

.header-desc {
  font-size: $font-body;
  color: $text-secondary;
  margin-top: $spacing-xs;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-shrink: 0;
}
</style>