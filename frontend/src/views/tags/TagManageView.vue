<template>
  <div class="tag-manage-view">
    <PageHeader :title="$t('nav.tagManage')">
      <template #actions>
        <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreateDialog">{{ $t('tagManage.createTag') }}</el-button>
      </template>
    </PageHeader>

    <div v-loading="loading" class="tag-content">
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="q"
          :placeholder="$t('tagManage.searchPlaceholder')"
          clearable
          class="search-input"
          :prefix-icon="Search"
          @input="onSearchInput"
        />
      </div>

      <div v-for="ns in filteredGroupedTags" :key="ns.namespace" class="namespace-group">
        <h3 class="ns-title">{{ ns.namespace }}</h3>
        <el-table :data="ns.tags" stripe class="tag-table" @row-click="openEditDialog">
          <el-table-column prop="name" :label="$t('common.columns.name')" width="140">
            <template #default="{ row }">
              <TagChip :tag="row" />
            </template>
          </el-table-column>
          <el-table-column :label="$t('tagManage.columns.color')" width="80">
            <template #default="{ row }">
              <span class="color-swatch" :style="{ background: row.color || 'var(--vs-accent)' }" />
            </template>
          </el-table-column>
          <el-table-column prop="description" :label="$t('common.columns.description')" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="cell-text">{{ row.description || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('tagManage.columns.pocCount')" width="80">
            <template #default="{ row }">
              <span class="cell-count">{{ row.poc_count }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('common.columns.actions')" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button v-if="canEdit" text size="small" @click.stop="openEditDialog(row)">{{ $t('common.action.edit') }}</el-button>
                <el-button v-if="canEdit" text size="small" type="danger" @click.stop="handleDelete(row)">{{ $t('common.action.delete') }}</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-if="!filteredGroupedTags.length && !loading" class="empty-area">
        <EmptyState icon="Collection" :title="q ? $t('tagManage.noMatch') : $t('tagManage.noTags')" :description="q ? $t('tagManage.tryOtherKeywords') : $t('tagManage.noneCreated')" />
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? $t('tagManage.editTag') : $t('tagManage.createTag')" width="420">
      <el-form ref="formRef" :model="tagForm" :rules="tagRules" label-width="80px">
        <el-form-item :label="$t('tagManage.fields.namespace')" prop="namespace">
          <el-select v-model="tagForm.namespace" allow-create filterable :placeholder="$t('tagManage.placeholders.namespace')">
            <el-option v-for="ns in namespaces" :key="ns" :label="ns" :value="ns" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('tagManage.fields.tagName')" prop="name">
          <el-input v-model="tagForm.name" :placeholder="$t('tagManage.placeholders.tagName')" />
        </el-form-item>
        <el-form-item :label="$t('tagManage.fields.color')" prop="color">
          <el-color-picker v-model="tagForm.color" />
        </el-form-item>
        <el-form-item :label="$t('tagManage.fields.description')" prop="description">
          <el-input v-model="tagForm.description" :placeholder="$t('tagManage.placeholders.description')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.action.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">{{ $t('common.action.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { listTags, createTag, updateTag, deleteTag, listNamespaces } from '@/api/tag'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import TagChip from '@/components/common/TagChip.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { TagItem } from '@/types/tag'

const { canEdit } = usePermission()
const { t } = useI18n()

const loading = ref(true)
const tags = ref<TagItem[]>([])
const namespaces = ref<string[]>([])
const q = ref('')
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()

const tagForm = ref({
  namespace: 'general',
  name: '',
  color: '#4a8cba',
  description: '',
})

const tagRules = {
  namespace: [{ required: true, message: t('tagManage.rules.namespace'), trigger: 'blur' }],
  name: [{ required: true, message: t('tagManage.rules.tagName'), trigger: 'blur' }],
}

const filteredGroupedTags = computed(() => {
  const kw = q.value.toLowerCase().trim()
  const map = new Map<string, TagItem[]>()
  for (const tag of tags.value) {
    // 搜索过滤：匹配标签名或命名空间
    if (kw) {
      const matchName = tag.name.toLowerCase().includes(kw)
      const matchNs = (tag.namespace || 'general').toLowerCase().includes(kw)
      if (!matchName && !matchNs) continue
    }
    const ns = tag.namespace || 'general'
    if (!map.has(ns)) map.set(ns, [])
    map.get(ns)!.push(tag)
  }
  return Array.from(map.entries()).map(([namespace, tags]) => ({ namespace, tags }))
})

async function loadData() {
  loading.value = true
  try {
    const [tagRes, nsRes] = await Promise.all([
      listTags({ page_size: 200 }),
      listNamespaces(),
    ])
    tags.value = tagRes.items
    namespaces.value = nsRes
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  // 搜索为客户端过滤，无需重新请求
}

function openCreateDialog() {
  isEditing.value = false
  editingId.value = null
  tagForm.value = { namespace: 'general', name: '', color: '#4a8cba', description: '' }
  dialogVisible.value = true
}

function openEditDialog(tag: any) {
  isEditing.value = true
  editingId.value = tag.id
  tagForm.value = {
    namespace: tag.namespace || 'general',
    name: tag.name,
    color: tag.color || '#4a8cba',
    description: tag.description || '',
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      await updateTag(editingId.value, tagForm.value)
      ElMessage.success(t('tagManage.messages.updateSuccess'))
    } else {
      await createTag(tagForm.value)
      ElMessage.success(t('tagManage.messages.createSuccess'))
    }
    dialogVisible.value = false
    loadData()
  } catch {
    // handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(tag: any) {
  try {
    await deleteTag(tag.id)
    ElMessage.success(t('tagManage.messages.deleteSuccess'))
    loadData()
  } catch {
    // handled by interceptor
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.tag-content {
  display: flex;
  flex-direction: column;
  gap: $spacing-xl;
}

.search-bar {
  margin-bottom: 0;
}

.search-input {
  width: 320px;
}

.namespace-group {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
}

.ns-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  padding: $spacing-lg;
  margin: 0;
  border-bottom: 1px solid $border-color;
}

.tag-table {
  cursor: pointer;
}

.color-swatch {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: $radius-sm;
  vertical-align: middle;
}

.cell-text {
  color: $text-secondary;
  font-size: $font-caption;
}

.cell-count {
  font-variant-numeric: tabular-nums;
  color: $text-secondary;
}

.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  line-height: 1;

  :deep(.el-button) {
    margin: 0;
    height: 24px;
    padding: 0 8px;
    justify-content: center;
  }
}

.empty-area {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
}
</style>