<template>
  <div class="empty-state">
    <div class="empty-icon">
      <el-icon :size="48"><component :is="icon" /></el-icon>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-desc">{{ description }}</p>
    <el-button v-if="action" type="primary" @click="action.handler">{{ action.label }}</el-button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon?: string
  title: string
  description?: string
  action?: { label: string; handler: () => void }
}>()
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-xxl * 2;
  text-align: center;
}

.empty-icon {
  color: $text-disabled;
  margin-bottom: $spacing-lg;
}

.empty-title {
  font-size: $font-title;
  font-weight: 500;
  color: $text-secondary;
  margin-bottom: $spacing-sm;
}

.empty-desc {
  font-size: $font-body;
  color: $text-disabled;
  margin-bottom: $spacing-xl;
  max-width: 360px;
}
</style>