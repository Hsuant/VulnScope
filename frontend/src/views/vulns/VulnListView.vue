<template>
  <div class="vuln-list-view">
    <PageHeader title="CVE 列表" description="CVE 漏洞数据展示与维护，支持搜索、筛选、删除与批量删除">
      <template #actions>
        <el-button :icon="Upload" @click="handleExport" :disabled="!selectedIds.length">导出</el-button>
        <el-button v-if="canEdit" :icon="Download" @click="goImport">导入 CVE</el-button>
        <el-button v-if="canEdit" type="primary" :icon="Plus" @click="goCreate">新建 CVE</el-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="q"
        placeholder="搜索 CVE 编号或标题..."
        clearable
        class="filter-search"
        :prefix-icon="Search"
        @keyup.enter="search"
      />
      <el-select v-model="severity" placeholder="严重级别" clearable class="filter-select">
        <el-option v-for="s in SEVERITY_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button :icon="Refresh" @click="resetFilters" class="filter-btn">清空</el-button>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.length" class="batch-bar">
      <span class="batch-info">已选 {{ selectedIds.length }} 项</span>
      <el-button size="small" :icon="Upload" @click="handleExport">批量导出</el-button>
      <el-button v-if="canEdit" size="small" type="danger" :icon="Delete" @click="handleBatchDelete">批量删除</el-button>
    </div>

    <!-- 数据表格 -->
    <el-table
      :data="items"
      v-loading="loading"
      stripe
      class="vuln-table"
      height="calc(100vh - 340px)"
      row-class-name="clickable-row"
      @selection-change="onSelectionChange"
      @row-click="onRowClick"
    >
      <el-table-column type="selection" width="40" />
      <el-table-column prop="cve_id" label="CVE 编号" width="160" align="center">
        <template #default="{ row }">
          <span class="cve-id">{{ row.cve_id }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="240" align="center" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="cell-text">{{ row.title || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="级别" width="80" align="center">
        <template #default="{ row }">
          <SeverityBadge v-if="row.severity" :severity="row.severity" />
          <span v-else class="cell-text">-</span>
        </template>
      </el-table-column>
      <el-table-column label="CVSS" width="72" align="center">
        <template #default="{ row }">
          <span class="cell-count">{{ row.cvss != null ? row.cvss.toFixed(1) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="POC 数" width="72" align="center">
        <template #default="{ row }">
          <span class="cell-count">{{ row.poc_count }}</span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="150" align="center">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.updated_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" align="center" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button text size="small" type="primary" @click.stop="viewDetail(row)">详情</el-button>
            <el-button v-if="canEdit" text size="small" type="danger" :icon="Delete" @click.stop="handleDelete(row)">删除</el-button>
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
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadData"
        @size-change="loadData"
      />
    </div>

    <!-- 确认对话框：单条删除 -->
    <ConfirmDialog
      v-model:visible="singleDeleteVisible"
      title="确认删除"
      :message="`确定要删除 CVE ${deleteTarget?.cve_id ?? ''} 吗？此操作不可恢复。`"
      type="danger"
      @confirm="confirmSingleDelete"
    />

    <!-- 确认对话框：批量删除 -->
    <ConfirmDialog
      v-model:visible="deleteDialogVisible"
      title="确认删除"
      :message="`确定要删除选中的 ${selectedIds.length} 个 CVE 吗？此操作不可恢复。`"
      type="danger"
      @confirm="confirmBatchDelete"
    />

    <!-- 导出格式选择对话框 -->
    <ConfirmDialog
      v-model:visible="exportDialogVisible"
      title="导出 CVE"
      message="选择导出格式："
      confirm-text="导出"
      @confirm="confirmExport"
    >
      <template #default>
        <el-radio-group v-model="exportFormat" class="export-format-group">
          <el-radio value="json">JSON（包含完整字段，可再导入）</el-radio>
          <el-radio value="yaml">YAML</el-radio>
        </el-radio-group>
      </template>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete, Download, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { deleteVuln, deleteVulnsBatch, exportVulns, listVulns } from '@/api/vuln'
import { SEVERITY_OPTIONS } from '@/utils/constants'
import { formatDate } from '@/utils/format'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import SeverityBadge from '@/components/common/SeverityBadge.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import type { VulnItem } from '@/types/vuln'

const router = useRouter()
const { canEdit } = usePermission()

const items = ref<VulnItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const q = ref('')
const severity = ref('')
const selectedIds = ref<number[]>([])
const deleteTarget = ref<VulnItem | null>(null)
const singleDeleteVisible = ref(false)
const deleteDialogVisible = ref(false)
const exportDialogVisible = ref(false)
const exportFormat = ref<'json' | 'yaml'>('json')

/** 加载列表数据，透传筛选与分页参数。 */
async function loadData() {
  loading.value = true
  try {
    const res = await listVulns({
      page: page.value,
      page_size: pageSize.value,
      severity: severity.value || undefined,
      q: q.value || undefined,
    })
    items.value = res.items
    total.value = res.total
  } catch {
    // 错误已由拦截器统一提示
  } finally {
    loading.value = false
  }
}

/** 执行搜索并回到第一页。 */
function search() {
  page.value = 1
  loadData()
}

/** 清空筛选条件并重新加载。 */
function resetFilters() {
  q.value = ''
  severity.value = ''
  page.value = 1
  loadData()
}

/** 单击行跳转到 CVE 详情页（跳过勾选列与操作列，避免误触）。 */
function onRowClick(row: VulnItem, column: { type?: string; label?: string }) {
  if (column?.type === 'selection' || column?.label === '操作') return
  router.push(`/vulns/${row.id}`)
}

/** 跳转到 CVE 详情页（操作列「详情」按钮）。 */
function viewDetail(vuln: VulnItem) {
  router.push(`/vulns/${vuln.id}`)
}

/** 跳转到新建 CVE 页（功能预留）。 */
function goCreate() {
  router.push('/vulns/new')
}

/** 跳转到导入 CVE 页（功能预留）。 */
function goImport() {
  router.push('/vulns/import')
}

/** 表格勾选变化时同步已选 ID 列表。 */
function onSelectionChange(selection: any[]) {
  selectedIds.value = selection.map((s) => s.id)
}

/** 打开单条删除确认框。 */
function handleDelete(row: VulnItem) {
  deleteTarget.value = row
  singleDeleteVisible.value = true
}

/** 确认删除单条 CVE，成功后刷新列表。 */
async function confirmSingleDelete() {
  singleDeleteVisible.value = false
  const target = deleteTarget.value
  if (!target) return
  try {
    await deleteVuln(target.id)
    ElMessage.success('删除成功')
    deleteTarget.value = null
    loadData()
  } catch {
    // 错误已由拦截器统一提示
  }
}

/** 打开批量删除确认框。 */
function handleBatchDelete() {
  if (!selectedIds.value.length) return
  deleteDialogVisible.value = true
}

/** 确认批量删除选中 CVE，成功后清空勾选并刷新列表。 */
async function confirmBatchDelete() {
  deleteDialogVisible.value = false
  try {
    await deleteVulnsBatch(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    loadData()
  } catch {
    // 错误已由拦截器统一提示
  }
}

/** 打开导出格式选择对话框，未选中时提示。 */
function handleExport() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先选择要导出的 CVE')
    return
  }
  exportDialogVisible.value = true
}

/** 确认导出：按所选格式下载文件。 */
async function confirmExport() {
  exportDialogVisible.value = false
  try {
    const res = await exportVulns(selectedIds.value, exportFormat.value)
    const blob = new Blob([res.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cves-export.${exportFormat.value === 'json' ? 'json' : 'yaml'}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    // 错误已由拦截器统一提示
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.vuln-list-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.filter-bar {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  align-items: center;
}

.filter-search {
  width: 260px;
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

.export-format-group {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  padding: $spacing-xs 0;
}

.vuln-table {
  flex: 1;

  :deep(.clickable-row) {
    cursor: pointer;
  }
}

.cve-id {
  color: $accent;
  font-weight: 500;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: $font-caption;
}

.cell-text {
  color: $text-secondary;
  font-size: $font-caption;
}

.cell-count {
  font-variant-numeric: tabular-nums;
  color: $text-secondary;
}

.cell-time {
  color: $text-disabled;
  font-size: $font-caption;
}

.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;

  :deep(.el-button) {
    margin: 0;
    height: 24px;
    padding: 0 6px;
    justify-content: center;
  }
}

.pagination-wrap {
  flex-shrink: 0;
  padding-top: $spacing-lg;
}
</style>