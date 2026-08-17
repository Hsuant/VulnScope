<template>
  <div v-loading="loading" class="poc-detail-view">
    <PageHeader :title="poc?.name || 'POC 详情'">
      <template #actions>
        <el-button @click="$router.push('/pocs')">返回</el-button>
        <el-button v-if="canEdit" :icon="Edit" @click="$router.push(`/pocs/${pocId}/edit`)">编辑</el-button>
        <el-button v-if="canEdit" :icon="CopyDocument" @click="handleClone">克隆</el-button>
        <el-dropdown v-if="canEdit" trigger="click" @command="handleStatusChange">
          <el-button :icon="Refresh">
            {{ STATUS_MAP[poc?.status || ''] || poc?.status }}
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="s in allowedTransitions"
                :key="s"
                :command="s"
              >
                {{ STATUS_MAP[s] || s }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-if="canEdit" type="danger" :icon="Delete" @click="handleDelete">删除</el-button>
      </template>
    </PageHeader>

    <div v-if="poc" class="detail-grid">
      <!-- 左列：元数据 -->
      <div class="detail-left">
        <div class="meta-section">
          <h3 class="section-title">基本信息</h3>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">名称</span>
              <span class="meta-value mono">{{ poc.name }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">标题</span>
              <span class="meta-value">{{ poc.title || '-' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">严重级别</span>
              <span class="meta-value"><SeverityBadge :severity="poc.severity" /></span>
            </div>
            <div class="meta-item">
              <span class="meta-label">状态</span>
              <span class="meta-value"><StatusBadge :status="poc.status" /></span>
            </div>
            <div class="meta-item">
              <span class="meta-label">来源</span>
              <span class="meta-value">{{ SOURCE_MAP[poc.source] || poc.source }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">格式</span>
              <span class="meta-value">{{ FORMAT_MAP[poc.format] || poc.format }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">作者</span>
              <span class="meta-value">{{ poc.author || '-' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">版本</span>
              <span class="meta-value">v{{ poc.version }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">内容哈希</span>
              <span class="meta-value mono small">{{ poc.content_hash?.slice(0, 16) }}...</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">创建时间</span>
              <span class="meta-value">{{ formatDate(poc.created_at) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">更新时间</span>
              <span class="meta-value">{{ formatDate(poc.updated_at) }}</span>
            </div>
          </div>
        </div>

        <div v-if="poc.description" class="meta-section">
          <h3 class="section-title">描述</h3>
          <p class="description-text">{{ poc.description }}</p>
        </div>

        <div class="meta-section">
          <h3 class="section-title">关联信息</h3>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">CVE 编号</span>
              <span class="meta-value">
                <template v-if="poc.cve_ids?.length">
                  <el-tag v-for="cve in poc.cve_ids" :key="cve" size="small" class="cve-tag">{{ cve }}</el-tag>
                </template>
                <span v-else>-</span>
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">标签</span>
              <span class="meta-value">
                <template v-if="poc.tags?.length">
                  <TagChip v-for="tag in poc.tags" :key="tag.id" :tag="tag" class="detail-tag" />
                </template>
                <span v-else>-</span>
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">FOFA</span>
              <span class="meta-value">
                <code v-if="poc.fofa_syntax" class="fofa-syntax">{{ poc.fofa_syntax }}</code>
                <span v-else>-</span>
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Shodan</span>
              <span class="meta-value">
                <code v-if="poc.shodan_syntax" class="fofa-syntax">{{ poc.shodan_syntax }}</code>
                <span v-else>-</span>
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">PublicWWW</span>
              <span class="meta-value">
                <code v-if="poc.publicwww_syntax" class="fofa-syntax">{{ poc.publicwww_syntax }}</code>
                <span v-else>-</span>
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">参考链接</span>
              <span class="meta-value">
                <template v-if="poc.references?.length">
                  <a
                    v-for="(ref, i) in poc.references" :key="i"
                    :href="ref.url" target="_blank" rel="noopener noreferrer"
                    class="ref-link"
                  >{{ ref.label || ref.url }}</a>
                </template>
                <span v-else>-</span>
              </span>
            </div>
          </div>
        </div>

        <!-- 版本历史 -->
        <div class="meta-section">
          <h3 class="section-title">版本历史</h3>
          <div v-if="versions.length" class="version-list">
            <div v-for="v in versions" :key="v.id" class="version-item" @click="viewVersion(v)">
              <span class="version-seq">v{{ v.version_seq }}</span>
              <span class="version-time">{{ formatRelativeTime(v.changed_at) }}</span>
              <span class="version-hash">{{ v.content_hash?.slice(0, 8) }}</span>
            </div>
          </div>
          <p v-else class="no-data">暂无版本记录</p>
        </div>

        <!-- 来源溯源 -->
        <div class="meta-section">
          <h3 class="section-title">来源溯源</h3>
          <div v-if="sourceRecords.length" class="source-list">
            <div v-for="r in sourceRecords" :key="r.id" class="source-item">
              <span class="source-type">{{ r.source_type }}</span>
              <span v-if="r.source_url" class="source-url">{{ r.source_url }}</span>
            </div>
          </div>
          <p v-else class="no-data">暂无溯源记录</p>
        </div>
      </div>

      <!-- 右列：代码/文档内容 -->
      <div class="detail-right">
        <div class="code-header">
          <h3 class="section-title">{{ isMarkdown ? '文档内容' : 'POC 内容' }}</h3>
          <div class="code-header-actions">
            <el-radio-group v-if="isMarkdown" v-model="mdView" size="small" class="md-view-switch">
              <el-radio-button value="rendered">渲染</el-radio-button>
              <el-radio-button value="raw">源码</el-radio-button>
            </el-radio-group>
            <el-button v-if="isMarkdown" size="small" text :icon="Download" @click="downloadMd">导出 .md</el-button>
            <el-button size="small" text :icon="CopyDocument" @click="copyContent">复制全文</el-button>
          </div>
        </div>
        <div class="code-container" :class="{ 'is-markdown': isMarkdown && mdView === 'rendered' }">
          <!-- Markdown 渲染 + 目录 -->
          <div v-if="isMarkdown && mdView === 'rendered'" class="md-content-wrap">
            <div class="md-rendered-scroll">
              <MarkdownRenderer :content="poc.content" @headings="(h: MdHeading[]) => (toc = h)" />
            </div>
            <aside v-if="toc.length" class="md-toc">
              <div class="md-toc-title">目录</div>
              <a
                v-for="h in toc"
                :key="h.slug"
                class="md-toc-item"
                :class="`md-toc-l${h.level}`"
                @click="scrollToHeading(h.slug)"
              >{{ h.text }}</a>
            </aside>
          </div>
          <!-- 源码 / 原始内容 -->
          <pre v-else class="code-block"><code>{{ poc.content }}</code></pre>
        </div>
      </div>
    </div>

    <!-- 克隆对话框 -->
    <el-dialog v-model="cloneDialogVisible" title="克隆 POC" width="420">
      <el-form>
        <el-form-item label="新名称" required>
          <el-input v-model="cloneName" placeholder="输入新 POC 名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cloneDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="cloning" @click="confirmClone">确认克隆</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, CopyDocument, Delete, Refresh, Download } from '@element-plus/icons-vue'
import { getPoc, deletePoc as apiDeletePoc, changePocStatus, clonePoc, getPocVersions, getPocSourceRecords } from '@/api/poc'
import { usePermission } from '@/composables/usePermission'
import { formatDate, formatRelativeTime, copyToClipboard } from '@/utils/format'
import { STATUS_MAP, SOURCE_MAP, FORMAT_MAP, STATUS_TRANSITIONS } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import SeverityBadge from '@/components/common/SeverityBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TagChip from '@/components/common/TagChip.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import MarkdownRenderer from '@/components/poc/MarkdownRenderer.vue'
import type { MdHeading } from '@/utils/markdown'
import type { PocDetail, PocVersion, PocSourceRecord } from '@/types/poc'

const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()

const pocId = computed(() => Number(route.params.id))
const loading = ref(true)
const poc = ref<PocDetail | null>(null)
const versions = ref<PocVersion[]>([])
const sourceRecords = ref<PocSourceRecord[]>([])
const cloneDialogVisible = ref(false)
const cloneName = ref('')
const cloning = ref(false)
// Markdown 视图模式：渲染 / 源码
const mdView = ref<'rendered' | 'raw'>('rendered')
const toc = ref<MdHeading[]>([])

const isMarkdown = computed(() => poc.value?.format === 'markdown')

const allowedTransitions = computed(() => {
  if (!poc.value) return []
  return STATUS_TRANSITIONS[poc.value.status] || []
})

async function loadData() {
  loading.value = true
  try {
    const [pocData, verData, srcData] = await Promise.all([
      getPoc(pocId.value),
      getPocVersions(pocId.value),
      getPocSourceRecords(pocId.value),
    ])
    poc.value = pocData
    versions.value = verData
    sourceRecords.value = srcData
  } catch {
    router.push('/pocs')
  } finally {
    loading.value = false
  }
}

function handleClone() {
  cloneName.value = poc.value?.name ? `${poc.value.name}-copy` : ''
  cloneDialogVisible.value = true
}

async function confirmClone() {
  if (!cloneName.value) {
    ElMessage.warning('请输入新名称')
    return
  }
  cloning.value = true
  try {
    const newPoc = await clonePoc(pocId.value, cloneName.value)
    ElMessage.success('克隆成功')
    cloneDialogVisible.value = false
    router.push(`/pocs/${newPoc.id}`)
  } catch {
    // handled by interceptor
  } finally {
    cloning.value = false
  }
}

async function handleStatusChange(status: string) {
  try {
    await changePocStatus(pocId.value, status)
    ElMessage.success('状态更新成功')
    loadData()
  } catch {
    // handled by interceptor
  }
}

async function handleDelete() {
  try {
    await apiDeletePoc(pocId.value)
    ElMessage.success('删除成功')
    router.push('/pocs')
  } catch {
    // handled by interceptor
  }
}

async function copyContent() {
  if (poc.value?.content) {
    await copyToClipboard(poc.value.content)
    ElMessage.success('已复制到剪贴板')
  }
}

function downloadMd() {
  if (!poc.value?.content) return
  const blob = new Blob([poc.value.content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${poc.value.name || 'poc'}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function scrollToHeading(slug: string) {
  const el = document.getElementById(slug)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function viewVersion(v: PocVersion) {
  ElMessage.info(`查看版本 v${v.version_seq} 请使用后端 API`)
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.poc-detail-view {
  height: 100%;
}

.detail-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: $spacing-xl;
  height: calc(100vh - 180px);
}

.detail-left {
  overflow-y: auto;
  padding-right: $spacing-sm;
}

.detail-right {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.meta-section {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-lg;
  margin-bottom: $spacing-lg;
}

.section-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-lg;
}

.meta-grid {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.meta-item {
  display: flex;
  gap: $spacing-sm;
  font-size: $font-body;
  line-height: 1.6;
}

.meta-label {
  color: $text-secondary;
  width: 96px;
  flex-shrink: 0;
  white-space: nowrap;
}

.meta-value {
  color: $text-primary;
  flex: 1;
  min-width: 0;
  word-break: break-all;

  &.mono {
    font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
    font-size: $font-caption;
  }

  &.small {
    font-size: $font-caption;
  }
}

.description-text {
  color: $text-secondary;
  font-size: $font-body;
  line-height: 1.6;
  margin: 0;
}

.cve-tag {
  margin-right: 4px;
  margin-bottom: 4px;
}

.detail-tag {
  margin-right: 4px;
  margin-bottom: 4px;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.version-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm 0;
  border-bottom: 1px solid $border-subtle;
  cursor: pointer;
  transition: color $transition-fast;

  &:hover {
    color: $accent;
  }

  &:last-child {
    border-bottom: none;
  }
}

.version-seq {
  font-weight: 600;
  color: $accent;
  font-size: $font-caption;
  width: 24px;
}

.version-time {
  font-size: $font-caption;
  color: $text-secondary;
  flex: 1;
}

.version-hash {
  font-size: $font-caption;
  color: $text-disabled;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-sm;

  .section-title {
    margin-bottom: 0;
  }
}

.code-container {
  flex: 1;
  background: $bg-tertiary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  overflow: auto;
  padding: $spacing-lg;
}

.code-block {
  margin: 0;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
  color: $text-primary;
  white-space: pre;
  word-wrap: normal;
}

.code-header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.md-view-switch {
  :deep(.el-radio-button__inner) {
    padding: 5px 12px;
  }
}

// Markdown 渲染布局
.code-container.is-markdown {
  padding: 0;
}

.md-content-wrap {
  display: flex;
  height: 100%;
  min-height: 0;
}

.md-rendered-scroll {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: $spacing-xl $spacing-xl $spacing-xl $spacing-lg;
}

.md-toc {
  width: 200px;
  flex-shrink: 0;
  overflow-y: auto;
  padding: $spacing-lg;
  border-left: 1px solid $border-color;
  background: $bg-tertiary;
}

.md-toc-title {
  font-size: $font-caption;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: $spacing-sm;
}

.md-toc-item {
  display: block;
  font-size: $font-caption;
  line-height: 1.5;
  color: $text-secondary;
  cursor: pointer;
  padding: 2px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color $transition-fast;

  &:hover {
    color: $accent;
  }

  &.md-toc-l2 { padding-left: 0; font-weight: 500; color: $text-primary; }
  &.md-toc-l3 { padding-left: 12px; }
  &.md-toc-l4 { padding-left: 24px; }
  &.md-toc-l5,
  &.md-toc-l6 { padding-left: 36px; }
}

.no-data {
  color: $text-disabled;
  font-size: $font-body;
  margin: 0;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.source-item {
  display: flex;
  gap: $spacing-sm;
  font-size: $font-caption;
  color: $text-secondary;
}

.source-type {
  font-weight: 500;
  color: $text-primary;
}

.ref-link {
  display: block;
  color: $accent;
  font-size: $font-caption;
  word-break: break-all;
  line-height: 1.6;
  & + & { margin-top: 4px; }
  &:hover { text-decoration: underline; }
}
</style>