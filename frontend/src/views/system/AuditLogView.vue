<template>
  <div class="audit-log-view">
    <PageHeader title="审计日志" description="所有写操作的全量审计记录" />

    <div class="filter-bar">
      <el-select v-model="action" placeholder="操作类型" clearable class="filter-select">
        <el-option v-for="(label, key) in ACTION_MAP" :key="key" :label="label" :value="key" />
      </el-select>
      <el-select v-model="resourceType" placeholder="资源类型" clearable class="filter-select">
        <el-option label="POC" value="poc" />
        <el-option label="用户" value="user" />
        <el-option label="标签" value="tag" />
      </el-select>
      <el-input v-model="userId" placeholder="用户 ID" class="filter-input" />
      <el-button :icon="Search" type="primary" @click="search">筛选</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe class="audit-table" height="calc(100vh - 320px)" @row-click="expandDetail">
      <el-table-column label="时间" width="160">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="username" label="用户" width="100" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <span class="action-text">{{ ACTION_MAP[row.action] || row.action }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="resource_type" label="资源" width="72" />
      <el-table-column prop="resource_id" label="资源 ID" width="80" />
      <el-table-column label="IP" width="120">
        <template #default="{ row }">
          <span class="cell-text">{{ row.ip || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="详情" min-width="200">
        <template #default="{ row }">
          <span v-if="row.detail" class="detail-summary" @click.stop="showDetail(row)">
            {{ detailSummary(row.detail) }}
          </span>
          <span v-else class="cell-text">-</span>
        </template>
      </el-table-column>
    </el-table>

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

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="审计详情" width="600">
      <pre class="detail-json">{{ JSON.stringify(selectedDetail, null, 2) }}</pre>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { listAuditLogs } from '@/api/audit'
import { formatDate } from '@/utils/format'
import { ACTION_MAP } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import type { AuditLogItem } from '@/types/audit'

const items = ref<AuditLogItem[]>([])
const loading = ref(true)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const action = ref('')
const resourceType = ref('')
const userId = ref('')
const detailVisible = ref(false)
const selectedDetail = ref<any>(null)

async function loadData() {
  loading.value = true
  try {
    const res = await listAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      action: action.value || undefined,
      resource_type: resourceType.value || undefined,
      user_id: userId.value ? Number(userId.value) : undefined,
    })
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

function detailSummary(detail: any): string {
  if (!detail) return '-'
  const parts: string[] = []
  if (detail.filename) parts.push(detail.filename)
  if (detail.before) parts.push(`before: ${Object.keys(detail.before).join(',')}`)
  if (detail.after) parts.push(`after: ${Object.keys(detail.after).join(',')}`)
  if (detail.poc_name) parts.push(detail.poc_name)
  return parts.join(' | ') || JSON.stringify(detail).slice(0, 80)
}

function expandDetail(row: AuditLogItem) {
  if (row.detail) {
    selectedDetail.value = row.detail
    detailVisible.value = true
  }
}

function showDetail(row: AuditLogItem) {
  selectedDetail.value = row.detail
  detailVisible.value = true
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.filter-bar {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  align-items: center;
}

.filter-select {
  width: 150px;
}

.filter-input {
  width: 120px;
}

.audit-table {
  cursor: pointer;
}

.action-text {
  color: $accent;
  font-size: $font-caption;
}

.cell-text {
  color: $text-secondary;
  font-size: $font-caption;
}

.cell-time {
  color: $text-disabled;
  font-size: $font-caption;
}

.detail-summary {
  color: $text-secondary;
  font-size: $font-caption;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.detail-json {
  background: $bg-tertiary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-lg;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  color: $text-primary;
  line-height: 1.5;
  overflow: auto;
  max-height: 400px;
  margin: 0;
  white-space: pre;
}

.pagination-wrap {
  padding-top: $spacing-lg;
}
</style>