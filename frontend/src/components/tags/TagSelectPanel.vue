<template>
  <div class="tag-select-panel">
    <div class="select-group">
      <!-- 厂商（Vendor）下拉：数据来源于标签命名空间 Vendor -->
      <TagNamespaceSelect
        v-model="vendorTagId"
        namespace="Vendor"
        :placeholder="$t('tagSelect.vendorPlaceholder')"
        popper-class="tag-select-popper"
        @change="onVendorChange"
        @clear="onVendorClear"
      />
      <!-- 产品（OSS）下拉：数据来源于标签命名空间 OSS -->
      <TagNamespaceSelect
        v-model="ossTagId"
        namespace="OSS"
        :placeholder="$t('tagSelect.ossPlaceholder')"
        popper-class="tag-select-popper"
        @change="onOssChange"
        @clear="onOssClear"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 标签选择面板 — 厂商 + 产品（OSS）选择
 *
 * 包含两个独立的下拉列表：
 * 1. 厂商（Vendor）：数据来源于标签命名空间 Vendor
 * 2. 产品（OSS）：数据来源于标签命名空间 OSS
 *
 * 两个下拉列表相互独立，可单独选择也可联合选择。
 * 联合搜索时取 AND 关系（同时满足两个标签）。
 *
 * 均支持：
 * - 键盘输入实时搜索，自动过滤匹配选项
 * - 搜索不区分大小写，支持模糊匹配
 * - 键盘 ↑ / ↓ 方向键在选项中移动焦点，Enter 键确认选择
 * - 下拉列表展示所有匹配的选项
 * - 选中后在下拉框输入区域显示选中的标签名称
 */
import { ref } from 'vue'
import TagNamespaceSelect from './TagNamespaceSelect.vue'
import type { TagItem } from '@/types/tag'

const emit = defineEmits<{
  change: [vendor: TagItem | null, oss: TagItem | null]
  clear: []
}>()

// ── 选中值 ────────────────────────────────────────────────────────
const vendorTagId = ref<number | null>(null)
const ossTagId = ref<number | null>(null)
const selectedVendor = ref<TagItem | null>(null)
const selectedOss = ref<TagItem | null>(null)

/** 厂商变更（独立，不清除 OSS） */
function onVendorChange(_val: number | null, tag: TagItem | null) {
  selectedVendor.value = tag
  emit('change', selectedVendor.value, selectedOss.value)
}

/** 厂商清空（独立，不清除 OSS） */
function onVendorClear() {
  vendorTagId.value = null
  selectedVendor.value = null
  emit('change', selectedVendor.value, selectedOss.value)
}

/** 产品变更 */
function onOssChange(_val: number | null, tag: TagItem | null) {
  selectedOss.value = tag
  emit('change', selectedVendor.value, selectedOss.value)
}

/** 产品清空 */
function onOssClear() {
  ossTagId.value = null
  selectedOss.value = null
  emit('change', selectedVendor.value, selectedOss.value)
}

defineExpose({
  reset() {
    vendorTagId.value = null
    ossTagId.value = null
    selectedVendor.value = null
    selectedOss.value = null
  },
  getVendorId() {
    return vendorTagId.value
  },
  getOssId() {
    return ossTagId.value
  },
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.tag-select-panel {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: $spacing-sm;
  min-width: 0;
}

.select-group {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: $spacing-sm;
  flex: 1 1 auto;
  min-width: 0;

  :deep(.tag-namespace-select) {
    flex: 1 1 156px;
    min-width: 100px;
  }
}
</style>