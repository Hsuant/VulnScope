<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <p class="confirm-message">{{ message }}</p>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">{{ $t('common.action.cancel') }}</el-button>
      <el-button
        :type="type === 'danger' ? 'danger' : 'primary'"
        :loading="loading"
        @click="$emit('confirm')"
      >
        {{ confirmText || $t('common.title.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
useI18n()

defineProps<{
  visible: boolean
  title: string
  message: string
  confirmText?: string
  type?: 'danger' | 'primary'
  loading?: boolean
  width?: string
}>()

defineEmits<{
  'update:visible': [value: boolean]
  confirm: []
}>()
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.confirm-message {
  color: $text-secondary;
  font-size: $font-body;
  line-height: 1.6;
}
</style>