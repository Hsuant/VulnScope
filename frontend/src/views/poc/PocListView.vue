<template>
  <div class="poc-list-view">
    <PageHeader title="POC 列表">
      <template #actions>
        <el-button :icon="Download" @click="handleExport" :disabled="!selectedIds.length">
          导出
        </el-button>
        <el-button :icon="Upload" @click="$router.push('/pocs/import')" v-if="canEdit">
          导入 POC
        </el-button>
        <el-button type="primary" :icon="Plus" @click="$router.push('/pocs/new')" v-if="canEdit">
          新建 POC
        </el-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="filters.q"
        placeholder="搜索名称、标题、描述..."
        clearable
        class="filter-search"
        :prefix-icon="Search"
        @keyup.enter="search"
      />
      <el-select v-model="filters.severity" placeholder="严重级别" clearable multiple collapse-tags class="filter-select">
        <el-option v-for="s in SEVERITY_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable multiple collapse-tags class="filter-select">
        <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filters.source" placeholder="来源" clearable multiple collapse-tags class="filter-select">
        <el-option v-for="s in SOURCE_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filters.format" placeholder="格式" clearable multiple collapse-tags class="filter-select">
        <el-option v-for="s in FORMAT_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button :icon="Refresh" @click="resetFilters" class="filter-btn">清空</el-button>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.length" class="batch-bar">
      <span class="batch-info">已选 {{ selectedIds.length }} 项</span>
      <el-select v-if="canEdit" v-model="batchStatus" placeholder="批量改状态" size="small" class="batch-select" @change="handleBatchStatus">
        <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button size="small" :icon="Download" @click="handleExport">批量导出</el-button>
      <el-button v-if="canEdit" size="small" type="danger" :icon="Delete" @click="handleBatchDelete">批量删除</el-button>
    </div>

    <!-- 表格 -->
    <el-table
      :data="items"
      v-loading="loading"
      stripe
      @selection-change="onSelectionChange"
      @row-click="(row: any) => $router.push(`/pocs/${row.id}`)"
      class="poc-table"
      row-class-name="poc-row"
      height="calc(100vh - 340px)"
    >
      <el-table-column type="selection" width="40" />
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="poc-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="poc-title">{{ row.title || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="级别" width="80">
        <template #default="{ row }">
          <SeverityBadge :severity="row.severity" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <StatusBadge :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column label="来源" width="72">
        <template #default="{ row }">
          <span class="cell-text">{{ SOURCE_MAP[row.source] || row.source }}</span>
        </template>
      </el-table-column>
      <el-table-column label="格式" width="100">
        <template #default="{ row }">
          <span class="cell-text">{{ FORMAT_MAP[row.format] || row.format }}</span>
        </template>
      </el-table-column>
      <el-table-column label="标签" min-width="140">
        <template #default="{ row }">
          <div class="tag-cell">
            <TagChip v-for="tag in row.tags.slice(0, 3)" :key="tag.id" :tag="tag" />
            <span v-if="row.tags.length > 3" class="tag-more">+{{ row.tags.length - 3 }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="CVE" width="130" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="cell-text">{{ row.cve_ids?.join(', ') || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="作者" width="90" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="cell-text">{{ row.author || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="140">
        <template #default="{ row }">
          <span class="cell-time">{{ formatRelativeTime(row.updated_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button text size="small" @click.stop="$router.push(`/pocs/${row.id}`)">查看</el-button>
            <el-button v-if="canEdit" text size="small" type="primary" @click.stop="$router.push(`/pocs/${row.id}/edit`)">编辑</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadData"
        @size-change="loadData"
      />
    </div>

    <!-- 确认对话框 -->
    <ConfirmDialog
      v-model:visible="deleteDialogVisible"
      title="确认删除"
      :message="`确定要删除选中的 ${selectedIds.length} 个 POC 吗？此操作不可恢复。`"
      type="danger"
      @confirm="confirmBatchDelete"
    />

    <ConfirmDialog
      v-model:visible="exportDialogVisible"
      title="导出 POC"
      message="选择导出格式："
      confirm-text="导出"
      @confirm="confirmExport"
    >
      <template #default>
        <el-radio-group v-model="exportFormat" class="export-format-group">
          <el-radio value="json">JSON（包含完整元数据）</el-radio>
          <el-radio value="nuclei-yaml">Nuclei YAML（纯模板）</el-radio>
        </el-radio-group>
      </template>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Download, Upload, Delete } from '@element-plus/icons-vue'
import { listPocs, deletePoc, changePocStatus } from '@/api/poc'
import { exportPocs } from '@/api/import-export'
import { usePermission } from '@/composables/usePermission'
import { formatRelativeTime } from '@/utils/format'
import { SEVERITY_OPTIONS, STATUS_OPTIONS, SOURCE_OPTIONS, FORMAT_OPTIONS, SOURCE_MAP, FORMAT_MAP } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import SeverityBadge from '@/components/common/SeverityBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TagChip from '@/components/common/TagChip.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import type { PocListItem } from '@/types/poc'

const router = useRouter()
const { canEdit } = usePermission()

const items = ref<PocListItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedIds = ref<number[]>([])
const batchStatus = ref('')
const deleteDialogVisible = ref(false)
const exportDialogVisible = ref(false)
const exportFormat = ref('json')

const filters = reactive({
  q: '',
  severity: [] as string[],
  status: [] as string[],
  source: [] as string[],
  format: [] as string[],
})

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onSelectionChange(selection: any[]) {
  selectedIds.value = selection.map((s: any) => s.id)
}

async function loadData() {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.q) params.q = filters.q
    if (filters.severity.length) params.severity = filters.severity.join(',')
    if (filters.status.length) params.status = filters.status.join(',')
    if (filters.source.length) params.source = filters.source.join(',')
    if (filters.format.length) params.format = filters.format.join(',')

    const res = await listPocs(params)
    items.value = res.items
    total.value = res.total
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  loadData()
}

function resetFilters() {
  filters.q = ''
  filters.severity = []
  filters.status = []
  filters.source = []
  filters.format = []
  page.value = 1
  loadData()
}

watch(filters, () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    loadData()
  }, 300)
}, { deep: true })

async function handleBatchStatus(status: string) {
  if (!selectedIds.value.length) return
  try {
    for (const id of selectedIds.value) {
      await changePocStatus(id, status)
    }
    ElMessage.success('批量状态更新成功')
    batchStatus.value = ''
    loadData()
  } catch {
    // handled by interceptor
  }
}

function handleBatchDelete() {
  if (!selectedIds.value.length) return
  deleteDialogVisible.value = true
}

async function confirmBatchDelete() {
  deleteDialogVisible.value = false
  try {
    for (const id of selectedIds.value) {
      await deletePoc(id)
    }
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    loadData()
  } catch {
    // handled by interceptor
  }
}

function handleExport() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先选择要导出的 POC')
    return
  }
  exportDialogVisible.value = true
}

async function confirmExport() {
  exportDialogVisible.value = false
  try {
    const res = await exportPocs(selectedIds.value, exportFormat.value)
    const blob = new Blob([res.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pocs-export.${exportFormat.value === 'json' ? 'json' : 'yaml'}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    // handled by interceptor
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.poc-list-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  align-items: center;
}

.filter-search {
  width: 220px;
}

.filter-select {
  width: 130px;
}

.filter-btn {
  flex-shrink: 0;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  background: rgba($accent, 0.06);
  border: 1px solid rgba($accent, 0.15);
  border-radius: $radius-md;
  margin-bottom: $spacing-md;
}

.batch-info {
  font-size: $font-body;
  color: $accent;
  margin-right: $spacing-sm;
}

.batch-select {
  width: 130px;
}

.poc-table {
  flex: 1;
}

.poc-row {
  cursor: pointer;
}

.poc-name {
  font-weight: 500;
  color: $accent;
}

.poc-title {
  color: $text-secondary;
}

.cell-text {
  color: $text-secondary;
  font-size: $font-caption;
}

.cell-time {
  color: $text-disabled;
  font-size: $font-caption;
}

.tag-cell {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  align-items: center;
}

.tag-more {
  font-size: $font-caption;
  color: $text-disabled;
}

.pagination-wrap {
  flex-shrink: 0;
}

.export-format-group {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  margin-top: $spacing-sm;
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
</style>