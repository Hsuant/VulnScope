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
      @row-click="handleRowClick"
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
      <el-table-column label="操作" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button text size="small" type="primary" @click.stop="goToDetail(row.id)">查看</el-button>
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

    <!-- ── 快速预览抽屉 ──────────────────────────────────── -->
    <el-drawer
      v-model="drawerVisible"
      direction="rtl"
      size="420px"
      :before-close="handleDrawerClose"
    >
      <template #header>
        <div class="drawer-header">
          <span class="drawer-title">{{ selectedPoc?.name || 'POC 预览' }}</span>
          <el-dropdown
            v-if="searchSyntaxes.length"
            trigger="click"
            @command="copySyntax"
          >
            <el-button size="small" class="search-btn">
              {{ searchSyntaxes[0].label }} <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="s in searchSyntaxes" :key="s.key" :command="s">
                  <span>{{ s.label }}</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>

      <div v-loading="drawerLoading" class="drawer-body">
        <template v-if="selectedPoc">
          <!-- 危险等级 + CVE -->
          <div class="info-row">
            <SeverityBadge :severity="selectedPoc.severity" />
            <span class="cve-text">{{ cveText }}</span>
          </div>
          <!-- 来源 -->
          <div class="source-row">
            <span class="meta-label">来源</span>
            <span>{{ SOURCE_MAP[selectedPoc.source] || selectedPoc.source }}</span>
          </div>

          <!-- 简介 -->
          <div class="section">
            <div class="section-label">简介</div>
            <div class="section-content text">{{ selectedPoc.description || '暂无描述' }}</div>
          </div>

          <!-- {{BASE_URL}}/路径 -->
          <div class="section">
            <div class="section-label">路径</div>
            <div class="section-content mono">{{ previewPath || '暂无可解析路径' }}</div>
          </div>

          <!-- 数据包 -->
          <div class="section">
            <div class="section-label">POC / EXP</div>
            <div v-if="previewPacket" class="packet-wrap">
              <pre class="packet-block"><code>{{ previewPacket }}</code></pre>
              <el-button size="small" text class="packet-copy" @click="copyPacket">复制</el-button>
            </div>
            <div v-else class="section-content">暂无可解析数据包</div>
          </div>
        </template>
        <div v-else class="drawer-empty">暂无数据</div>
      </div>
    </el-drawer>

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
          <el-radio value="nuclei">Nuclei YAML（纯模板）</el-radio>
        </el-radio-group>
      </template>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search, Refresh, Download, Upload, Delete, ArrowDown } from '@element-plus/icons-vue'
import { listPocs, getPoc, deletePoc, changePocStatus } from '@/api/poc'
import { exportPocs } from '@/api/import-export'
import { usePermission } from '@/composables/usePermission'
import { formatRelativeTime, copyToClipboard } from '@/utils/format'
import { SEVERITY_OPTIONS, STATUS_OPTIONS, SOURCE_OPTIONS, FORMAT_OPTIONS, SOURCE_MAP, FORMAT_MAP } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import SeverityBadge from '@/components/common/SeverityBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TagChip from '@/components/common/TagChip.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import type { PocListItem, PocDetail } from '@/types/poc'

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

// ── 抽屉状态 ──────────────────────────────────────────────────
const drawerVisible = ref(false)
const drawerLoading = ref(false)
const selectedPoc = ref<PocDetail | null>(null)

// ── 资产搜集语法列表 ──────────────────────────────────────────
const searchSyntaxes = computed(() => {
  const poc = selectedPoc.value
  if (!poc) return []
  const list: { key: string; label: string; value: string }[] = []
  if (poc.fofa_syntax) list.push({ key: 'fofa', label: 'FOFA', value: poc.fofa_syntax })
  if (poc.shodan_syntax) list.push({ key: 'shodan', label: 'Shodan', value: poc.shodan_syntax })
  return list
})

const cveText = computed(() => {
  const ids = selectedPoc.value?.cve_ids
  if (!ids?.length) return '-'
  if (ids.length === 1) return ids[0]
  return `${ids[0]} +${ids.length - 1}`
})

// ── 内容解析 ──────────────────────────────────────────────────
const previewPath = computed(() => {
  const poc = selectedPoc.value
  if (!poc) return ''
  return extractPath(poc)
})

const previewPacket = computed(() => {
  const poc = selectedPoc.value
  if (!poc) return ''
  return extractPacket(poc)
})

function extractPath(poc: PocDetail): string {
  const content = poc.content || ''
  const lines = content.split('\n')

  // 在 requests/http 块内找 path 列表，取第一个值
  let inBlock = false
  let inPath = false
  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim()
    if (/^requests?\s*[:[]/.test(trimmed) || /^http\s*[:[]/.test(trimmed)) {
      inBlock = true
      continue
    }
    if (!inBlock) continue
    // 遇到 path: 行，标记并继续
    if (/^path\s*:/.test(trimmed)) {
      // 行内直接跟值：path: '{{BaseURL}}/xxx'
      const inline = trimmed.match(/^path\s*:\s*["']?(\{\{baseurl\s*\}\}\/[^\s"']*)["']?\s*$/i)
      if (inline) return inline[1]
      // 行内数组：path: ['{{BaseURL}}/xxx', ...]
      const inlineArr = trimmed.match(/^path\s*:\s*\[?\s*["']?(\{\{baseurl\s*\}\}\/[^\s"',\]]*)/i)
      if (inlineArr) return inlineArr[1]
      // 值是列表格式，下一行开始找
      inPath = true
      continue
    }
    if (inPath) {
      // 匹配 - '{{BaseURL}}/xxx' 或 - "{{BaseURL}}/xxx" 或 - {{BaseURL}}/xxx
      const itemMatch = trimmed.match(/^-\s*["']?(\{\{baseurl\s*\}\}\/[^\s"']*)["']?\s*$/i)
      if (itemMatch) return itemMatch[1]
      // 如果遇到新字段且不再是列表项，退出 path 模式
      if (/^\w/.test(trimmed) && !/^-\s/.test(trimmed)) inPath = false
    }
  }

  // 通用回退：查找 {{BaseURL}} 或路径模式
  for (const line of lines) {
    const trimmed = line.trim()
    const baseMatch = trimmed.match(/\{\{baseurl\s*\}\}(\/[^\s,)'"]*)/i)
    if (baseMatch) return baseMatch[1]
  }
  return ''
}

function extractPacket(poc: PocDetail): string {
  const content = poc.content || ''
  try {
    if (poc.format === 'nuclei') {
      const yaml = loadYaml(content)
      if (yaml) {
        const reqs = yaml.requests || yaml.http || []
        if (reqs.length) {
          return reconstructNucleiRequest(reqs[0])
        }
      }
    }
  } catch { /* ignore parse errors */ }

  // 通用回退：提取代码中的数据包部分
  const lines = content.split('\n')
  // 尝试提取 raw 块（nuclei raw 请求）
  const rawBlocks = extractRawBlocks(lines)
  if (rawBlocks.length) return rawBlocks.join('\n')

  // 提取 pocsuite3 的 requests 调用
  const pocsuiteMatch = content.match(/requests\.(?:get|post|put|delete)\s*\([^)]+\)/i)
  if (pocsuiteMatch) return pocsuiteMatch[0]

  // 返回内容的前 40 行作为数据包预览
  return lines.slice(0, 40).join('\n')
}

function loadYaml(content: string): any {
  try {
    // 动态 import js-yaml，避免 ESM 包在 Vue SFC 中的树摇问题
    const lines = content.split('\n')
    const result: any = {}
    let current: any = result
    // 简易 YAML 解析：只提取顶层的 requests/http/path/method/headers/body
    const stack: any[] = [result]
    const indentStack = [-1]
    for (const line of lines) {
      const trimmed = line.trimEnd()
      if (!trimmed || trimmed.startsWith('#') || /^---/.test(trimmed)) continue
      const indent = line.length - line.trimStart().length
      while (indentStack.length > 1 && indent <= indentStack[indentStack.length - 1]) {
        stack.pop()
        indentStack.pop()
      }
      const match = trimmed.match(/^(\w[\w-]*)\s*:\s*(.*)$/)
      if (match) {
        const key = match[1]
        const val = match[2].trim()
        if (val === '' || val === '|' || val === '>') {
          const obj: any = {}
          stack[stack.length - 1][key] = obj
          stack.push(obj)
          indentStack.push(indent)
        } else if (val.startsWith('[') || val.startsWith('{')) {
          try { stack[stack.length - 1][key] = JSON.parse(val) } catch { stack[stack.length - 1][key] = val }
        } else if (val === 'true') { stack[stack.length - 1][key] = true }
        else if (val === 'false') { stack[stack.length - 1][key] = false }
        else { stack[stack.length - 1][key] = val.replace(/^["']|["']$/g, '') }
      }
      // 处理数组项
      const arrMatch = trimmed.match(/^\s*-\s+(.+)$/)
      if (arrMatch) {
        // 找到父级数组
        const parent = stack[stack.length - 1]
        const lastKey = Object.keys(parent).pop()
        if (lastKey && Array.isArray(parent[lastKey])) {
          parent[lastKey].push(arrMatch[1].replace(/^["']|["']$/g, ''))
        }
      }
    }
    return result
  } catch {
    return null
  }
}

function reconstructNucleiRequest(req: any): string {
  const method = req.method || 'GET'
  const path = Array.isArray(req.path) ? req.path[0] : (req.path || '/')
  const headers = req.headers || {}
  const body = req.body || ''

  let packet = `${method} ${path} HTTP/1.1\r\n`
  packet += `Host: {{BASE_URL}}\r\n`
  for (const [k, v] of Object.entries(headers)) {
    packet += `${k}: ${v}\r\n`
  }
  if (body) {
    if (!Object.keys(headers).some(h => h.toLowerCase() === 'content-type')) {
      packet += 'Content-Type: application/x-www-form-urlencoded\r\n'
    }
    packet += '\r\n'
    packet += body
  }
  return packet
}

function extractRawBlocks(lines: string[]): string[] {
  const blocks: string[] = []
  let inRaw = false
  let current: string[] = []
  for (const line of lines) {
    if (/^\s*raw\s*[|>]\s*$/.test(line)) {
      inRaw = true
      current = []
      continue
    }
    if (inRaw) {
      if (/^\s*$/.test(line) || /^\w/.test(line)) {
        if (current.length) {
          blocks.push(current.join('\n'))
          current = []
        }
        inRaw = false
      } else {
        current.push(line.replace(/^\s{2,}/, ''))
      }
    }
  }
  if (current.length) blocks.push(current.join('\n'))
  return blocks
}

// ── 事件处理 ──────────────────────────────────────────────────
function handleRowClick(row: PocListItem) {
  openDrawer(row.id)
}

function goToDetail(id: number) {
  router.push(`/pocs/${id}`)
}

async function openDrawer(id: number) {
  drawerVisible.value = true
  drawerLoading.value = true
  try {
    selectedPoc.value = await getPoc(id)
  } catch {
    selectedPoc.value = null
    ElMessage.error('加载 POC 详情失败')
  } finally {
    drawerLoading.value = false
  }
}

function handleDrawerClose() {
  drawerVisible.value = false
  selectedPoc.value = null
}

async function copySyntax(syntax: { key: string; label: string; value: string }) {
  try {
    await copyToClipboard(syntax.value)
    ElMessage.success(`已复制 ${syntax.label} 语法`)
  } catch {
    ElMessage.error('复制失败')
  }
}

async function copyPacket() {
  if (!previewPacket.value) return
  try {
    await copyToClipboard(previewPacket.value)
    ElMessage.success('已复制数据包')
  } catch {
    ElMessage.error('复制失败')
  }
}

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

// ── 抽屉样式 ──────────────────────────────────────────────────
:deep(.el-drawer) {
  background: var(--vs-bg-primary);
  color: var(--vs-text-primary);
}

:deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 20px 0;
  color: var(--vs-text-primary);
}

:deep(.el-drawer__body) {
  padding: 12px 20px 20px;
  color: var(--vs-text-primary);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: $spacing-md;
}

.drawer-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.search-btn {
  white-space: nowrap;
}

.drawer-body {
  padding: 0;
}

.drawer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: $text-disabled;
}

// ── 信息行 ────────────────────────────────────────────────────
.info-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;
}

.cve-text {
  font-size: $font-body;
  color: $text-primary;
  font-weight: 500;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
}

.source-row {
  font-size: $font-body;
  color: $text-secondary;
  margin-bottom: $spacing-lg;

  .meta-label {
    color: $text-disabled;
    margin-right: $spacing-xs;
  }
}

// ── 区块 ──────────────────────────────────────────────────────
.section {
  margin-bottom: $spacing-lg;
}

.section-label {
  font-size: $font-caption;
  color: $text-secondary;
  font-weight: 600;
  margin-bottom: $spacing-xs;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-content {
  font-size: $font-body;
  color: $text-primary;
  line-height: 1.6;
  word-break: break-all;

  &.text {
    color: $text-secondary;
    display: -webkit-box;
    -webkit-line-clamp: 6;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &.mono {
    font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
    font-size: $font-caption;
    color: var(--vs-accent);
    background: var(--vs-bg-tertiary);
    padding: $spacing-xs $spacing-sm;
    border-radius: $radius-sm;
    display: inline-block;
  }
}

// ── 数据包 ────────────────────────────────────────────────────
.packet-wrap {
  position: relative;
  background: $bg-tertiary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  overflow: hidden;
}

.packet-block {
  margin: 0;
  padding: $spacing-md;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  color: $text-primary;
  white-space: pre;
  overflow-x: auto;
  max-height: 360px;
}

.packet-copy {
  position: absolute;
  top: $spacing-xs;
  right: $spacing-xs;
}
</style>