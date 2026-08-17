<template>
  <div class="poc-list-view">
    <PageHeader title="POC 列表">
      <template #actions>
        <el-button :icon="Upload" @click="handleExport" :disabled="!selectedIds.length">
          导出
        </el-button>
        <el-button :icon="Download" @click="$router.push('/pocs/import')" v-if="canEdit">
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
      <el-button size="small" :icon="Upload" @click="handleExport">批量导出</el-button>
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
      <el-table-column prop="title" label="名称" min-width="360" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="poc-name">{{ row.title || row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="级别" width="80" align="center">
        <template #default="{ row }">
          <SeverityBadge :severity="row.severity" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <StatusBadge :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column label="标签" width="150" align="center">
        <template #default="{ row }">
          <div class="tag-cell">
            <TagChip v-for="tag in row.tags.slice(0, 3)" :key="tag.id" :tag="tag" />
            <span v-if="row.tags.length > 3" class="tag-more">+{{ row.tags.length - 3 }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="CVE" width="130" align="center" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="cell-text">{{ row.cve_ids?.join(', ') || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="作者" width="90" align="center" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="cell-text">{{ row.author || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="150" align="center">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.updated_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button text size="small" type="primary" @click.stop="goToDetail(row.id)">详情</el-button>
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
          <!-- 概要卡片：等级 / CVE / 来源 -->
          <div class="summary-card">
            <div class="summary-top">
              <SeverityBadge :severity="selectedPoc.severity" />
              <span class="source-chip">{{ SOURCE_MAP[selectedPoc.source] || selectedPoc.source }}</span>
            </div>
            <div class="summary-cve">
              <span class="meta-label">CVE</span>
              <span class="cve-text">{{ cveText }}</span>
            </div>
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
              <div class="packet-toolbar">
                <span class="packet-lang">raw</span>
                <el-button size="small" text class="packet-copy" :icon="CopyDocument" @click="copyPacket">复制</el-button>
              </div>
              <pre class="packet-block"><code>{{ previewPacket }}</code></pre>
            </div>
            <div v-else class="section-content">暂无可解析数据包</div>
          </div>

          <!-- 参考链接 -->
          <div class="section">
            <div class="section-label">
              参考链接
              <span v-if="selectedPoc.references?.length" class="count-badge">{{ selectedPoc.references.length }}</span>
            </div>
            <div v-if="selectedPoc.references?.length" class="ref-list">
              <a
                v-for="(ref, i) in selectedPoc.references" :key="i"
                :href="ref.url" target="_blank" rel="noopener noreferrer"
                class="ref-link"
              >
                <el-icon class="ref-icon"><Link /></el-icon>
                <span class="ref-text">{{ ref.label || ref.url }}</span>
              </a>
            </div>
            <div v-else class="section-content">暂无参考链接</div>
          </div>

          <!-- 底部操作 -->
          <div class="drawer-footer">
            <el-button type="primary" plain class="footer-btn" @click="goToDetail(selectedPoc.id)">
              查看完整详情
            </el-button>
          </div>
        </template>
        <div v-else class="drawer-empty">暂无数据</div>
      </div>
    </el-drawer>

    <!-- 确认对话框：单条删除 -->
    <ConfirmDialog
      v-model:visible="singleDeleteVisible"
      title="确认删除"
      :message="`确定要删除 POC ${(deleteTarget?.title || deleteTarget?.name) ?? ''} 吗？此操作不可恢复。`"
      type="danger"
      @confirm="confirmSingleDelete"
    />

    <!-- 确认对话框：批量删除 -->
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
import { Plus, Search, Refresh, Download, Upload, Delete, ArrowDown, Link, CopyDocument } from '@element-plus/icons-vue'
import { listPocs, getPoc, deletePoc, changePocStatus } from '@/api/poc'
import { exportPocs } from '@/api/import-export'
import { usePermission } from '@/composables/usePermission'
import { formatDate, copyToClipboard } from '@/utils/format'
import { SEVERITY_OPTIONS, STATUS_OPTIONS, SOURCE_OPTIONS, FORMAT_OPTIONS, SOURCE_MAP } from '@/utils/constants'
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
const deleteTarget = ref<PocListItem | null>(null)
const singleDeleteVisible = ref(false)
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
  if (poc.publicwww_syntax) list.push({ key: 'publicwww', label: 'PublicWWW', value: poc.publicwww_syntax })
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
  const lines = content.split('\n')

  // 1. 优先提取 raw 块 —— 最忠实于协议原文（含空行与 body）
  const rawBlocks = extractRawBlocks(lines)
  if (rawBlocks.length) return rawBlocks.join('\n\n')

  // 2. 无 raw 时，尝试 nuclei 结构化解析再重建
  if (poc.format === 'nuclei') {
    try {
      const yaml = loadYaml(content)
      if (yaml) {
        const reqs = yaml.requests || yaml.http || []
        if (reqs?.length) {
          const req = reqs[0]
          if (req?.raw) return Array.isArray(req.raw) ? req.raw.join('\n') : String(req.raw)
          return reconstructNucleiRequest(req)
        }
      }
    } catch { /* ignore parse errors */ }
  }

  // 3. 提取 pocsuite3 的 requests 调用
  const pocsuiteMatch = content.match(/requests\.(?:get|post|put|delete)\s*\([^)]+\)/i)
  if (pocsuiteMatch) return pocsuiteMatch[0]

  // 4. 回退：返回内容前 80 行作为数据包预览
  return lines.slice(0, 80).join('\n')
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

// 提取 nuclei / yaml 中的 raw 数据包块，忠实保留空行（HTTP header/body 分隔）与相对缩进。
// 支持四种写法：raw: |  /  raw:\n  - |  /  raw: "..."  /  raw: ["...","..."]
function extractRawBlocks(lines: string[]): string[] {
  const blocks: string[] = []
  const n = lines.length
  let i = 0
  while (i < n) {
    const m = lines[i].match(/^( *)(?:- )?raw\s*:\s*(.*)$/)
    if (!m) { i++; continue }
    const keyIndent = m[1].length
    const inline = m[2].trim()
    i++

    // raw: |- / raw: > / raw: |-2  （block scalar 直接跟在 key 后）
    if (/^[|>][-+]?[0-9]*$/.test(inline)) {
      const block = collectBlockScalar(lines, i, keyIndent)
      if (block) { blocks.push(block.content); i = block.nextIndex; continue }
    }

    // raw: "GET / HTTP/1.1\r\nHost: ...\r\n\r\nbody"  /  raw: ["...", "..."]
    if (inline.startsWith('"') || inline.startsWith("'") || inline.startsWith('[')) {
      const text = unescapeYamlString(inline)
      if (text) { blocks.push(text); continue }
    }

    // raw:\n  - |  \n    <content>   或   raw:\n  - "..."
    // 跳过中间空行，定位第一个列表项
    while (i < n && lines[i].trim() === '') i++
    if (i >= n) continue
    const itemMatch = lines[i].match(/^(\s*)-\s+(.*)$/)
    if (!itemMatch) continue
    const itemIndent = itemMatch[1].length
    const itemVal = itemMatch[2].trim()
    i++
    if (/^[|>][-+]?[0-9]*$/.test(itemVal)) {
      const block = collectBlockScalar(lines, i, itemIndent)
      if (block) { blocks.push(block.content); i = block.nextIndex; continue }
    }
    if (itemVal) { blocks.push(unescapeYamlString(itemVal)); continue }
  }
  return blocks
}

// 从 start 起收集一个 block scalar：以第一条内容行的缩进为基准，
// 保留其中空行（HTTP 分隔符），直到遇到缩进回落到 parentIndent 及以下的非空行。
function collectBlockScalar(
  lines: string[],
  start: number,
  parentIndent: number,
): { content: string; nextIndex: number } | null {
  const n = lines.length
  let i = start
  while (i < n && lines[i].trim() === '') i++
  if (i >= n) return null
  const first = lines[i]
  const baseIndent = first.length - first.trimStart().length
  if (baseIndent <= parentIndent) return null
  const collected: string[] = []
  while (i < n) {
    const l = lines[i]
    if (l.trim() === '') {
      collected.push('')
      i++
      continue
    }
    const indent = l.length - l.trimStart().length
    if (indent <= parentIndent) break // 缩进回落到父级，block 结束
    collected.push(l.slice(baseIndent))
    i++
  }
  while (collected.length && collected[collected.length - 1] === '') collected.pop()
  if (!collected.length) return null
  return { content: collected.join('\n'), nextIndex: i }
}

// 还原 YAML 字符串字面量：处理双引号转义、单引号 '' 转义、flow 数组。
function unescapeYamlString(s: string): string {
  let t = s.trim()
  if (t.startsWith('[')) {
    try {
      const arr = JSON.parse(t)
      if (Array.isArray(arr)) return arr.map(x => String(x)).join('\n')
    } catch { /* fallthrough */ }
  }
  const q = t[0]
  if (q !== '"' && q !== "'") return t
  if (t[t.length - 1] === q) t = t.slice(1, -1)
  if (q === '"') {
    return t
      .replace(/\\r\\n/g, '\r\n')
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\')
  }
  return t.replace(/''/g, "'")
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

/** 打开单条删除确认框。 */
function handleDelete(row: PocListItem) {
  deleteTarget.value = row
  singleDeleteVisible.value = true
}

/** 确认删除单条 POC，成功后刷新列表。 */
async function confirmSingleDelete() {
  singleDeleteVisible.value = false
  const target = deleteTarget.value
  if (!target) return
  try {
    await deletePoc(target.id)
    ElMessage.success('删除成功')
    deleteTarget.value = null
    loadData()
  } catch {
    // 错误已由拦截器统一提示
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
  justify-content: center;
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
  display: flex;
  flex-direction: column;
}

.drawer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: $text-disabled;
}

// ── 概要卡片 ──────────────────────────────────────────────────
.summary-card {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  padding: $spacing-md $spacing-lg;
  margin-bottom: $spacing-lg;
  background: var(--vs-bg-secondary);
  border: 1px solid var(--vs-border-subtle);
  border-radius: $radius-lg;
}

.summary-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-sm;
}

.source-chip {
  font-size: $font-caption;
  color: var(--vs-text-secondary);
  background: var(--vs-bg-tertiary);
  border: 1px solid var(--vs-border-subtle);
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.summary-cve {
  display: flex;
  align-items: baseline;
  gap: $spacing-xs;
}

.cve-text {
  font-size: $font-body;
  color: $text-primary;
  font-weight: 600;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
}

// ── 区块 ──────────────────────────────────────────────────────
.section {
  margin-bottom: $spacing-lg;
}

.section-label {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-size: $font-caption;
  color: $text-secondary;
  font-weight: 600;
  margin-bottom: $spacing-xs;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 5px;
  font-size: 11px;
  line-height: 1;
  color: var(--vs-text-inverse);
  background: var(--vs-accent);
  border-radius: 8px;
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
    border: 1px solid var(--vs-border-subtle);
    padding: $spacing-xs $spacing-sm;
    border-radius: $radius-sm;
    display: inline-block;
    max-width: 100%;
  }
}

.ref-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.ref-link {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-sm;
  color: var(--vs-text-secondary);
  font-size: $font-caption;
  background: var(--vs-bg-secondary);
  border: 1px solid var(--vs-border-subtle);
  border-radius: $radius-sm;
  transition: all $transition-fast;

  .ref-icon {
    flex-shrink: 0;
    color: var(--vs-accent);
    font-size: 14px;
  }

  .ref-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &:hover {
    color: var(--vs-accent);
    background: rgba(var(--vs-accent-rgb), 0.06);
    border-color: rgba(var(--vs-accent-rgb), 0.25);

    .ref-text { text-decoration: underline; }
  }
}

// ── 数据包 ────────────────────────────────────────────────────
.packet-wrap {
  background: var(--vs-bg-tertiary);
  border: 1px solid var(--vs-border-color);
  border-radius: $radius-md;
  overflow: hidden;
}

.packet-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px $spacing-xs 2px $spacing-sm;
  background: var(--vs-bg-secondary);
  border-bottom: 1px solid var(--vs-border-subtle);
}

.packet-lang {
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 11px;
  color: var(--vs-text-disabled);
  text-transform: uppercase;
  letter-spacing: 0.5px;
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
  max-height: 320px;
}

// ── 底部操作 ──────────────────────────────────────────────────
.drawer-footer {
  flex-shrink: 0;
  margin-top: auto;
  padding-top: $spacing-md;
  border-top: 1px solid var(--vs-border-subtle);

  .footer-btn {
    width: 100%;
  }
}
</style>