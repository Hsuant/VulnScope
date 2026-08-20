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

    <!-- 筛选栏（含标题） -->
    <div class="filter-bar">
      <span class="filter-bar-label">常规查询</span>
      <div class="query-fields">
        <el-input
          v-model="filters.q"
          placeholder="搜索名称、标题、描述..."
          clearable
          class="filter-search"
          :prefix-icon="Search"
          @keyup.enter="search"
        />
        <el-cascader
          v-model="filters.tagIds"
          :options="tagOptions"
          :props="{ multiple: true, emitPath: false, value: 'id', label: 'name' }"
          placeholder="按标签查询"
          clearable
          collapse-tags
          collapse-tags-tooltip
          class="filter-cascader"
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
      </div>
      <el-button type="primary" :icon="Search" @click="search" class="filter-queries__btn">查询</el-button>
      <el-button :icon="Refresh" @click="resetFilters" class="filter-btn">清空</el-button>
    </div>

    <!-- 产品查询面板：基于标签命名空间（Vendor / OSS）的厂商 / 产品选择 -->
    <div class="product-query-bar">
      <span class="product-query-label">产品查询</span>
      <div class="query-fields">
        <TagSelectPanel
          ref="tagSelectPanelRef"
          @change="onTagSelectChange"
          @clear="onTagSelectClear"
        />
        <el-select v-model="versionStartOp" placeholder="≥" class="op-select" @change="doProductQuery">
          <el-option label="不限" value="any" />
          <el-option label=">" value="gt" />
          <el-option label=">=" value="gte" />
          <el-option label="<" value="lt" />
          <el-option label="<=" value="lte" />
          <el-option label="==" value="eq" />
        </el-select>
        <el-input
          v-model="versionStart"
          placeholder="2.3.0"
          clearable
          class="version-input"
          @keyup.enter="doProductQuery"
        />
        <el-select v-model="versionEndOp" placeholder="≤" class="op-select" @change="doProductQuery">
          <el-option label="不限" value="any" />
          <el-option label=">" value="gt" />
          <el-option label=">=" value="gte" />
          <el-option label="<" value="lt" />
          <el-option label="<=" value="lte" />
          <el-option label="==" value="eq" />
        </el-select>
        <el-input
          v-model="versionEnd"
          placeholder="2.3.5"
          clearable
          class="version-input"
          @keyup.enter="doProductQuery"
        />
      </div>
      <el-button type="primary" :icon="Search" :loading="productQueryLoading" @click="doProductQuery" class="filter-queries__btn">
        查询
      </el-button>
      <el-button :icon="Refresh" @click="resetProductQuery" class="filter-btn">清空</el-button>
    </div>

    <!-- 产品查询状态条：仅产品模式下显示 -->
    <div v-if="productMode" class="product-status-row">
      <span class="product-mode-hint">
        <el-icon class="hint-icon"><InfoFilled /></el-icon>
        当前查询：{{ selectedVendorName ? `${selectedVendorName} : ` : '' }}{{ selectedOssName }}
        {{ versionStart ? `${versionStartOp || '≥'} ${versionStart}` : '' }}
        {{ versionEnd ? `～ ${versionEndOp || '≤'} ${versionEnd}` : '' }}
      </span>
      <el-button text size="small" type="primary" @click="exitProductMode">
        返回列表
      </el-button>
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

          <!-- 路径 -->
          <div class="section">
            <div class="section-label">
              路径
              <span v-if="previewPaths.length" class="count-badge">{{ previewPaths.length }}</span>
            </div>
            <div v-if="previewPaths.length" class="path-list">
              <div v-for="(p, i) in previewPaths" :key="i" class="path-item section-content mono">{{ p }}</div>
            </div>
            <div v-else class="section-content">暂无可解析路径</div>
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
import { load as loadYamlDoc } from 'js-yaml'
import { Plus, Search, Refresh, Download, Upload, Delete, ArrowDown, Link, CopyDocument, InfoFilled } from '@element-plus/icons-vue'
import { listPocs, getPoc, deletePoc, changePocStatus } from '@/api/poc'
import { listTags } from '@/api/tag'
import { exportPocs } from '@/api/import-export'
import { usePermission } from '@/composables/usePermission'
import { formatDate, copyToClipboard } from '@/utils/format'
import { SEVERITY_OPTIONS, STATUS_OPTIONS, SOURCE_OPTIONS, SOURCE_MAP } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import SeverityBadge from '@/components/common/SeverityBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TagChip from '@/components/common/TagChip.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import TagSelectPanel from '@/components/tags/TagSelectPanel.vue'
import type { PocListItem, PocDetail } from '@/types/poc'
import type { TagItem } from '@/types/tag'

const router = useRouter()
const { canEdit } = usePermission()

onMounted(() => {
  loadTagOptions()
  loadData()
})

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
  tagIds: [] as number[],
})

// ── 标签级联选项（一级命名空间 → 二级标签名）──────────────
const tagOptions = ref<{ id: string; name: string; children: { id: number; name: string }[] }[]>([])

/** 拉取全部标签并按命名空间分组成二级级联选项。 */
async function loadTagOptions() {
  try {
    const all: TagItem[] = []
    let p = 1
    const pageSize = 200
    while (true) {
      const res = await listTags({ page: p, page_size: pageSize })
      all.push(...res.items)
      if (res.items.length < pageSize || all.length >= (res.total || 0)) break
      p++
    }
    const group = new Map<string, TagItem[]>()
    for (const t of all) {
      if (!group.has(t.namespace)) group.set(t.namespace, [])
      group.get(t.namespace)!.push(t)
    }
    // 注意：props 中 value/label 字段名（id/name）作用于所有层级，
    // 因此一级（命名空间）对象也必须使用 id/name 键，否则命名空间不显示。
    tagOptions.value = [...group.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([ns, tags]) => ({
        id: ns,
        name: ns,
        children: tags
          .map(t => ({ id: t.id, name: t.name }))
          .sort((a, b) => a.name.localeCompare(b.name)),
      }))
  } catch {
    tagOptions.value = []
  }
}

// ── 产品查询状态（标签命名空间 Vendor / OSS 模式）───────────
const productMode = ref(false)
const productQueryLoading = ref(false)
const tagSelectPanelRef = ref<InstanceType<typeof TagSelectPanel>>()
const selectedVendorTag = ref<TagItem | null>(null)
const selectedOssTag = ref<TagItem | null>(null)
const versionStart = ref('')
const versionStartOp = ref('gte')
const versionEnd = ref('')
const versionEndOp = ref('lte')

/** 选中标签的显示名称（用于状态条） */
const selectedVendorName = computed(() => selectedVendorTag.value?.name || '')
const selectedOssName = computed(() => selectedOssTag.value?.name || '')

/** TagSelectPanel 选中变更回调 */
function onTagSelectChange(vendor: TagItem | null, oss: TagItem | null) {
  selectedVendorTag.value = vendor
  selectedOssTag.value = oss
}

/** TagSelectPanel 清空回调 */
function onTagSelectClear() {
  selectedVendorTag.value = null
  selectedOssTag.value = null
  productMode.value = false
}

/** 产品查询：基于选中的 Vendor / OSS 标签检索 POC。
 *  厂商和产品可单独查询也可联合查询（AND 关系：同时满足两个标签）。
 *  至少需选择一个标签。 */
async function doProductQuery() {
  const vendorId = tagSelectPanelRef.value?.getVendorId()
  const ossId = tagSelectPanelRef.value?.getOssId()

  if (!vendorId && !ossId) {
    ElMessage.warning('请至少选择一个厂商或产品')
    return
  }

  productQueryLoading.value = true
  productMode.value = true
  page.value = 1
  try {
    const params: Record<string, any> = {
      page: page.value,
      page_size: pageSize.value,
    }
    const vendorId = tagSelectPanelRef.value?.getVendorId()
    const ossId = tagSelectPanelRef.value?.getOssId()
    if (vendorId && ossId) {
      // 同时选中厂商和产品：AND 逻辑，POC 必须同时满足两个标签
      params.tag_ids_all = [vendorId, ossId].join(',')
    } else if (vendorId) {
      // 仅厂商：OR 逻辑（单标签无所谓 AND/OR）
      params.tag_ids = String(vendorId)
    } else if (ossId) {
      // 仅产品：OR 逻辑（单标签无所谓 AND/OR）
      params.tag_ids = String(ossId)
    }
    if (versionStart.value) {
      params.version_start = versionStart.value
      params.version_start_op = versionStartOp.value
    }
    if (versionEnd.value) {
      params.version_end = versionEnd.value
      params.version_end_op = versionEndOp.value
    }
    const res = await listPocs(params)
    items.value = res.items as any
    total.value = res.total
  } catch {
    items.value = []
    total.value = 0
  } finally {
    productQueryLoading.value = false
  }
}

function resetProductQuery() {
  productMode.value = false
  selectedVendorTag.value = null
  selectedOssTag.value = null
  versionStart.value = ''
  versionStartOp.value = 'gte'
  versionEnd.value = ''
  versionEndOp.value = 'lte'
  tagSelectPanelRef.value?.reset()
  page.value = 1
  loadData()
}

function exitProductMode() {
  productMode.value = false
  selectedVendorTag.value = null
  selectedOssTag.value = null
  versionStart.value = ''
  versionStartOp.value = 'gte'
  versionEnd.value = ''
  versionEndOp.value = 'lte'
  tagSelectPanelRef.value?.reset()
  page.value = 1
  loadData()
}

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
const previewPaths = computed<string[]>(() => {
  const poc = selectedPoc.value
  if (!poc) return []
  return extractPaths(poc)
})

const previewPacket = computed(() => {
  const poc = selectedPoc.value
  if (!poc) return ''
  return extractPacket(poc)
})

/** 收集 POC 的全部路径（多请求 × 每请求多 path），保持顺序并去重。 */
function extractPaths(poc: PocDetail): string[] {
  const content = poc.content || ''
  if (!content) return []

  const collected: string[] = []
  const seen = new Set<string>()
  const push = (p: string) => {
    const v = p.trim()
    if (v && !seen.has(v)) {
      seen.add(v)
      collected.push(v)
    }
  }

  // 1. nuclei：用 js-yaml 真正解析，遍历 http/requests 请求列表的全部 path
  if (poc.format === 'nuclei') {
    const obj = safeLoadYaml(content)
    const reqs = obj && (obj.http || obj.requests)
    if (Array.isArray(reqs) && reqs.length) {
      for (const req of reqs) {
        for (const p of pathsOf(req)) push(p)
      }
    }
    if (collected.length) return collected
  }

  // 2. 通用回退：扫描 {{BaseURL}}/xxx 形态（兼容非 nuclei 与解析失败的情况）
  for (const line of content.split('\n')) {
    const baseMatch = line.match(/\{\{baseurl\s*\}\}(\/[^\s,)'"]*)/i)
    if (baseMatch) push(baseMatch[1])
  }
  return collected
}

/** 从单个 nuclei 请求条目提取全部路径（raw 报文首行路径 + path 列表/标量）。 */
function pathsOf(req: any): string[] {
  if (!req || typeof req !== 'object') return []
  const out: string[] = []
  // raw 模式：从每段报文首行（如 `GET /xxx HTTP/1.1`）提取路径
  if (req.raw != null) {
    const rawStr = Array.isArray(req.raw) ? req.raw.map(String).join('\n') : String(req.raw)
    for (const seg of rawStr.split(/\r?\n\s*\r?\n/)) {
      const firstLine = seg.split(/\r?\n/)[0] || ''
      const m = firstLine.match(/^[A-Z]+\s+(\S+)\s*HTTP\//i)
      if (m) out.push(m[1])
    }
  }
  if (Array.isArray(req.path)) {
    for (const p of req.path) out.push(String(p))
  } else if (req.path) {
    out.push(String(req.path))
  }
  return out
}

function extractPacket(poc: PocDetail): string {
  const content = poc.content || ''
  if (!content) return ''
  const lines = content.split('\n')

  // 1. nuclei：用 js-yaml 真正解析 http/requests 请求列表，逐条重建 HTTP 报文
  if (poc.format === 'nuclei') {
    const obj = safeLoadYaml(content)
    const reqs = obj && (obj.http || obj.requests)
    if (Array.isArray(reqs) && reqs.length) {
      const packets = reqs.map(requestToPacket).filter(Boolean)
      if (packets.length) return packets.join('\n\n')
    }
    // js-yaml 解析失败时，退回原始 raw 块文本提取（块标量写法）
    const rawBlocks = extractRawBlocks(lines)
    if (rawBlocks.length) return rawBlocks.join('\n\n')
  }

  // 2. 提取 pocsuite3 的 requests 调用
  const pocsuiteMatch = content.match(/requests\.(?:get|post|put|delete)\s*\([^)]+\)/i)
  if (pocsuiteMatch) return pocsuiteMatch[0]

  // 3. 回退：返回内容前 80 行作为数据包预览
  return lines.slice(0, 80).join('\n')
}

/** 用 js-yaml 安全解析；失败或非对象时返回 null。 */
function safeLoadYaml(content: string): Record<string, any> | null {
  try {
    const obj = loadYamlDoc(content)
    if (obj && typeof obj === 'object' && !Array.isArray(obj)) return obj as Record<string, any>
    return null
  } catch {
    return null
  }
}

/** 把单个 nuclei 请求条目重建为 HTTP 报文；raw 优先于结构化字段。 */
function requestToPacket(req: any): string {
  if (!req || typeof req !== 'object') return ''
  if (req.raw != null) {
    return Array.isArray(req.raw) ? req.raw.map(String).join('\n') : String(req.raw)
  }
  const method = String(req.method || 'GET').toUpperCase()
  let path = '/'
  if (Array.isArray(req.path) && req.path.length) path = String(req.path[0])
  else if (req.path) path = String(req.path)
  const headers = req.headers && typeof req.headers === 'object' ? req.headers as Record<string, any> : {}
  const body = req.body != null ? String(req.body) : ''

  let packet = `${method} ${path} HTTP/1.1\r\n`
  packet += `Host: {{BaseURL}}\r\n`
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
  if (productMode.value && (selectedVendorTag.value || selectedOssTag.value)) {
    await doProductQuery()
    return
  }
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
    const tagIds = filters.tagIds.filter((id: any) => typeof id === 'number')
    if (tagIds.length) params.tag_ids = tagIds.join(',')

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
  filters.tagIds = []
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

</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.poc-list-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  padding: $spacing-sm $spacing-md;
  background: rgba($accent, 0.02);
  border: 1px solid rgba($accent, 0.06);
  border-radius: $radius-md;
  min-width: 0;
}

/* 常规/产品查询公用的字段区：单行、同间隔。
   flex:1 使两栏字段区在同等可用空间下渲染为等宽，从而「查询/清空」
   按钮左缘逐一平齐，末列（来源 vs 最高版本号）右缘对齐。 */
.query-fields {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: $spacing-sm;
  flex: 1 1 auto;
  min-width: 0;
}

/* 两栏标签样式统一（均为 4 字，宽度天然一致） */
.filter-bar-label,
.product-query-label {
  font-size: $font-caption;
  font-weight: 600;
  color: $text-secondary;
  white-space: nowrap;
  letter-spacing: 0.3px;
  margin-right: $spacing-xs;
  flex-shrink: 0;
}

/* 常规栏：搜索框为可变宽字段，吸收剩余空间使末列（来源）右缘贴齐字段区右缘 */
.filter-search {
  flex: 1 1 220px;
  min-width: 120px;
}

.filter-select {
  flex: 0 0 130px;
}

.filter-cascader {
  flex: 0 0 130px;
}

/* 常规/产品查询的「查询」「清空」按钮：共用类名、同一样式 */
.filter-queries__btn,
.filter-btn {
  flex-shrink: 0;
}

/* ── 产品查询面板 ── */
.product-query-bar {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  margin-bottom: $spacing-md;
  background: rgba($accent, 0.04);
  border: 1px solid rgba($accent, 0.12);
  border-radius: $radius-md;
  min-width: 0;
}

/* 产品栏：TagSelectPanel 内嵌的两个下拉框均设为等额可伸缩，
   二者 flex-grow 相同 → 平分剩余空间 → 渲染宽度始终相等；
   末列（最高版本号）仍贴齐字段区右缘。 */
:deep(.tag-select-panel) {
  flex: 1 1 auto;
  min-width: 200px;
}

:deep(.tag-select-panel .tag-namespace-select) {
  flex: 1 1 156px;
  min-width: 100px;
}

:deep(.op-select) {
  flex: 0 0 80px;
}

.version-input {
  flex: 0 0 130px;
}

/* ── 产品查询状态条（仅产品模式）── 与上方两栏解耦，独立成行，
   不挤压查询/清空按钮，避免内容被覆盖或遮挡。 */
.product-status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-sm;
  padding: $spacing-xs $spacing-md;
  margin-bottom: $spacing-md;
  background: rgba($accent, 0.06);
  border: 1px solid rgba($accent, 0.15);
  border-radius: $radius-md;
}

.product-mode-hint {
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  min-width: 0;
  font-size: $font-caption;
  color: $accent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  .hint-icon {
    flex-shrink: 0;
    font-size: 14px;
  }
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

.path-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;

  .path-item {
    display: block;
    max-width: 100%;
    white-space: nowrap;
    overflow-x: auto;
  }
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

<!-- 非 scoped：el-select 的下拉面板会被 teleport 到 body，
     不携带本组件 scope id，故用 popper-class 在全局作用域内渲染。 -->
<style lang="scss">
.tag-select-popper .option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}

.tag-select-popper .option-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-select-popper .option-slug {
  font-size: 12px;
  color: var(--vs-text-disabled);
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
}

.tag-select-popper .option-count {
  font-size: 11px;
  color: var(--vs-accent);
  white-space: nowrap;
}
</style>