<template>
  <div class="tag-manage-view">
    <PageHeader title="标签管理">
      <template #actions>
        <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreateDialog">新建标签</el-button>
      </template>
    </PageHeader>

    <div v-loading="loading" class="tag-content">
      <div v-for="ns in groupedTags" :key="ns.namespace" class="namespace-group">
        <h3 class="ns-title">{{ ns.namespace }}</h3>
        <el-table :data="ns.tags" stripe class="tag-table" @row-click="openEditDialog">
          <el-table-column prop="name" label="名称" width="140">
            <template #default="{ row }">
              <TagChip :tag="row" />
            </template>
          </el-table-column>
          <el-table-column label="颜色" width="80">
            <template #default="{ row }">
              <span class="color-swatch" :style="{ background: row.color || '#4a8cba' }" />
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="cell-text">{{ row.description || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="POC 数" width="80">
            <template #default="{ row }">
              <span class="cell-count">{{ row.poc_count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button v-if="canEdit" text size="small" @click.stop="openEditDialog(row)">编辑</el-button>
                <el-button v-if="canEdit" text size="small" type="danger" @click.stop="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-if="!groupedTags.length && !loading" class="empty-area">
        <EmptyState icon="Collection" title="暂无标签" description="尚未创建任何标签" />
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑标签' : '新建标签'" width="420">
      <el-form ref="formRef" :model="tagForm" :rules="tagRules" label-width="80px">
        <el-form-item label="命名空间" prop="namespace">
          <el-select v-model="tagForm.namespace" allow-create filterable placeholder="选择或输入命名空间">
            <el-option v-for="ns in namespaces" :key="ns" :label="ns" :value="ns" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签名" prop="name">
          <el-input v-model="tagForm.name" placeholder="标签名称" />
        </el-form-item>
        <el-form-item label="颜色" prop="color">
          <el-color-picker v-model="tagForm.color" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="tagForm.description" placeholder="描述信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listTags, createTag, updateTag, deleteTag, listNamespaces } from '@/api/tag'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import TagChip from '@/components/common/TagChip.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { TagItem } from '@/types/tag'

const { canEdit } = usePermission()

const loading = ref(true)
const tags = ref<TagItem[]>([])
const namespaces = ref<string[]>([])
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
  namespace: [{ required: true, message: '请输入命名空间', trigger: 'blur' }],
  name: [{ required: true, message: '请输入标签名', trigger: 'blur' }],
}

const groupedTags = computed(() => {
  const map = new Map<string, TagItem[]>()
  for (const tag of tags.value) {
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
      ElMessage.success('标签更新成功')
    } else {
      await createTag(tagForm.value)
      ElMessage.success('标签创建成功')
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
    ElMessage.success('标签已删除')
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
  flex-direction: column;
  align-items: center;
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