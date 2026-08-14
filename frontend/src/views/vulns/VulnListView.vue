<template>
  <div class="vuln-list-view">
    <PageHeader title="CVE 漏洞库" description="CVE 漏洞与 POC 关联管理" />

    <div class="filter-bar">
      <el-input v-model="q" placeholder="搜索 CVE 编号或标题..." clearable :prefix-icon="Search" class="filter-search" @keyup.enter="search" />
      <el-select v-model="severity" placeholder="严重级别" clearable class="filter-select">
        <el-option v-for="s in SEVERITY_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button :icon="Search" type="primary" @click="search">搜索</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe class="vuln-table" height="calc(100vh - 320px)">
      <el-table-column prop="cve_id" label="CVE 编号" width="160">
        <template #default="{ row }">
          <span class="cve-id">{{ row.cve_id }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="cell-text">{{ row.title || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="级别" width="80">
        <template #default="{ row }">
          <SeverityBadge v-if="row.severity" :severity="row.severity" />
          <span v-else class="cell-text">-</span>
        </template>
      </el-table-column>
      <el-table-column label="CVSS" width="72">
        <template #default="{ row }">
          <span class="cell-text">{{ row.cvss != null ? row.cvss.toFixed(1) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="POC 数" width="72">
        <template #default="{ row }">
          <span class="cell-count">{{ row.poc_count }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button text size="small" @click="viewVuln(row)">详情</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { listVulns } from '@/api/vuln'
import { SEVERITY_OPTIONS } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import SeverityBadge from '@/components/common/SeverityBadge.vue'
import type { VulnItem } from '@/types/vuln'

const router = useRouter()
const items = ref<VulnItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const q = ref('')
const severity = ref('')

async function loadData() {
  loading.value = true
  try {
    const res = await listVulns({ page: page.value, page_size: pageSize.value, severity: severity.value || undefined, q: q.value || undefined })
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

function viewVuln(vuln: VulnItem) {
  router.push(`/pocs?cve=${vuln.cve_id}`)
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

.filter-search {
  width: 260px;
}

.filter-select {
  width: 130px;
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

.pagination-wrap {
  padding-top: $spacing-lg;
}
</style>