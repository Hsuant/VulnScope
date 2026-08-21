<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder || $t('tagSelect.selectPlaceholder')"
    filterable
    remote
    :remote-method="onSearch"
    :loading="loading"
    clearable
    :multiple="multiple"
    :collapse-tags="collapseTags"
    :collapse-tags-tooltip="collapseTagsTooltip"
    :popper-class="popperClass"
    :default-first-option="true"
    :no-data-text="noDataText"
    :loading-text="$t('tagSelect.loading')"
    @change="onChange"
    @clear="onClear"
    @focus="onFocus"
    class="tag-namespace-select"
  >
    <el-option
      v-for="tag in filteredOptions"
      :key="tag.id"
      :label="tag.name"
      :value="tag.id"
    >
      <div class="tag-option-item">
        <span class="tag-option-color" :style="{ background: tag.color || 'var(--vs-accent)' }" />
        <span class="tag-option-name">{{ tag.name }}</span>
        <span class="tag-option-desc" v-if="tag.description">- {{ tag.description }}</span>
        <span class="tag-option-count" v-if="tag.poc_count != null">{{ tag.poc_count }} POC</span>
      </div>
    </el-option>
  </el-select>
</template>

<script setup lang="ts">
/**
 * 标签命名空间下拉选择组件
 *
 * 功能：
 * - 按命名空间（如 Vendor / OSS）从后端拉取标签列表
 * - 支持键盘输入实时搜索，客户端做不区分大小写的模糊匹配
 * - 支持键盘 ↑ / ↓ 方向键移动焦点，Enter 键确认选择（el-select 内置）
 * - 候选列表展示标签名、描述、POC 关联数
 * - 选中后下拉框显示选中的标签名称
 */
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listTags } from '@/api/tag'
import type { TagItem } from '@/types/tag'

const { t } = useI18n()

interface Props {
  /** 标签命名空间，如 "Vendor" / "OSS" */
  namespace: string
  /** v-model 绑定值（标签 ID，单数） */
  modelValue?: number | null
  /** 占位提示文本 */
  placeholder?: string
  /** 是否多选 */
  multiple?: boolean
  /** 多选时是否折叠标签 */
  collapseTags?: boolean
  /** 多选折叠时鼠标悬停 tooltip 展示全部 */
  collapseTagsTooltip?: boolean
  /** 下拉菜单自定义类名 */
  popperClass?: string
  /** 是否禁用 */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  placeholder: '',
  multiple: false,
  collapseTags: false,
  collapseTagsTooltip: false,
  popperClass: undefined,
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  change: [value: number | null, tag: TagItem | null]
  clear: []
}>()

// ── 状态 ──────────────────────────────────────────────────────────
const loading = ref(false)
const allTags = ref<TagItem[]>([])           // 命名空间下全部标签（缓存）
const displayTags = ref<TagItem[]>([])        // 当前展示的选项
const searchKeyword = ref('')                 // 当前搜索关键词
const hasFetched = ref(false)                 // 是否已拉取过

/** 当前展示的选项列表（透传给 el-option） */
const filteredOptions = computed<TagItem[]>(() => displayTags.value)

/** 无数据提示文本 */
const noDataText = computed(() => {
  if (loading.value) return ''
  if (searchKeyword.value) return t('tagSelect.noMatch')
  return t('tagSelect.searchHint')
})

// ── 数据加载与搜索 ────────────────────────────────────────────────

/** 拉取命名空间下的全部标签 */
async function fetchAllTags(): Promise<TagItem[]> {
  try {
    const res = await listTags({
      namespace: props.namespace,
      page: 1,
      page_size: 200,
    })
    return res.items || []
  } catch {
    return []
  }
}

/** 聚焦时加载默认列表 */
async function onFocus() {
  if (hasFetched.value) return
  hasFetched.value = true
  loading.value = true
  try {
    allTags.value = await fetchAllTags()
    displayTags.value = [...allTags.value]
  } finally {
    loading.value = false
  }
}

/**
 * 远程搜索回调：在已缓存的全部标签中做客户端模糊匹配，
 * 搜索不区分大小写，支持连续子串匹配（正向包含即为匹配）。
 */
function onSearch(keyword: string) {
  searchKeyword.value = keyword
  if (!keyword) {
    // 关键词为空 → 展示全部
    displayTags.value = [...allTags.value]
    return
  }
  const kw = keyword.toLowerCase()
  displayTags.value = allTags.value.filter(
    tag =>
      tag.name.toLowerCase().includes(kw) ||
      (tag.description && tag.description.toLowerCase().includes(kw)),
  )
}

// ── 事件 ──────────────────────────────────────────────────────────

function onChange(val: number | null) {
  emit('update:modelValue', val)
  const selected = allTags.value.find(t => t.id === val) || null
  emit('change', val, selected)
}

function onClear() {
  emit('clear')
}

// 命名空间变更时重置
watch(() => props.namespace, () => {
  allTags.value = []
  displayTags.value = []
  searchKeyword.value = ''
  hasFetched.value = false
})
</script>

<style scoped lang="scss">
.tag-namespace-select {
  width: 100%;
}

.tag-option-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  width: 100%;
}

.tag-option-color {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tag-option-name {
  font-weight: 500;
  flex-shrink: 0;
}

.tag-option-desc {
  font-size: 12px;
  color: var(--vs-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.tag-option-count {
  font-size: 11px;
  color: var(--vs-accent, #409eff);
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: auto;
}
</style>