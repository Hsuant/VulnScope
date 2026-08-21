<template>
  <div v-loading="loading" class="vuln-detail-view">
    <PageHeader :title="vuln?.cve_id || $t('nav.vulnDetail')" :description="vuln?.title || undefined">
      <template #actions>
        <el-button :icon="Back" @click="$router.push('/vulns')">{{ $t('vulnDetail.backToList') }}</el-button>
        <el-button :icon="Link" :loading="pocLoading" @click="goRelatedPoc">{{ $t('vulnDetail.relatedPoc') }}</el-button>
        <el-button v-if="canEdit" type="primary" :icon="Edit" @click="goEdit">{{ $t('common.action.edit') }}</el-button>
        <el-button v-if="canEdit" type="danger" plain :icon="Delete" @click="handleDelete">{{ $t('common.action.delete') }}</el-button>
      </template>
    </PageHeader>

    <div v-if="vuln" class="detail-body">
      <!-- 顶部指标条：一眼概览 -->
      <div class="metric-strip">
        <div class="metric severity-metric">
          <span class="metric-label">{{ $t('vulnDetail.metrics.severity') }}</span>
          <span class="metric-value">
            <SeverityBadge v-if="vuln.severity" :severity="vuln.severity" />
            <span v-else class="placeholder">{{ $t('vulnDetail.unrated') }}</span>
          </span>
        </div>

        <div class="metric-divider" />

        <div class="metric cvss-metric">
          <span class="cvss-num" :class="vuln.severity || 'info'">
            {{ vuln.cvss != null ? vuln.cvss.toFixed(1) : '—' }}
          </span>
          <div class="cvss-meta">
            <span class="metric-label">{{ $t('vulnDetail.metrics.cvss') }}</span>
            <span v-if="cvssVector.version" class="cvss-ver">v{{ cvssVector.version }}</span>
          </div>
        </div>

        <div class="metric-divider" />

        <div class="metric">
          <span class="metric-label">{{ $t('vulnDetail.metrics.vendor') }}</span>
          <span class="metric-value">{{ vuln.vendor || '—' }}</span>
        </div>

        <div class="metric-divider" />

        <div class="metric">
          <span class="metric-label">{{ $t('vulnDetail.relatedPoc') }}</span>
          <span class="metric-value">
            <el-link type="primary" :underline="false" @click="goRelatedPoc">{{ $t('vulnDetail.pocCount', { count: vuln.poc_count }) }}</el-link>
          </span>
        </div>

        <div class="metric-divider" />

        <div class="metric">
          <span class="metric-label">{{ $t('common.columns.updatedAt') }}</span>
          <span class="metric-value mono">{{ formatDate(vuln.updated_at) }}</span>
        </div>
      </div>

      <div class="sections">
        <!-- CVSS 指标向量 -->
        <section v-if="vuln.cvss_metrics" class="detail-section">
          <header class="section-head">
            <h3 class="section-title"><i class="title-bar" />{{ $t('vulnDetail.sections.cvssVector') }}</h3>
            <el-button text size="small" :icon="CopyDocument" @click="copyVector">{{ $t('vulnDetail.copyVector') }}</el-button>
          </header>
          <code class="vector-raw">{{ vuln.cvss_metrics }}</code>
          <div v-if="cvssVector.valid" class="vector-chips">
            <el-tag
              v-for="m in cvssVector.metrics"
              :key="m.key"
              size="small"
              effect="plain"
              class="vector-chip"
            >
              <span class="chip-key">{{ m.label }}</span>
              <span class="chip-sep">·</span>
              <span class="chip-val">{{ m.valueLabel }}</span>
            </el-tag>
          </div>
        </section>

        <!-- 漏洞描述 -->
        <section class="detail-section">
          <header class="section-head">
            <h3 class="section-title"><i class="title-bar" />{{ $t('vulnDetail.sections.description') }}</h3>
          </header>
          <MarkdownRenderer v-if="vuln.description" :content="vuln.description" class="prose" />
          <p v-else class="no-data">{{ $t('vulnDetail.noDescription') }}</p>
        </section>

        <!-- 受影响产品 -->
        <section class="detail-section">
          <header class="section-head">
            <h3 class="section-title"><i class="title-bar" />{{ $t('vulnDetail.sections.products') }}</h3>
            <span v-if="vuln.product?.length" class="section-count">{{ $t('vulnDetail.itemCount', { count: vuln.product.length }) }}</span>
          </header>
          <el-table
            v-if="vuln.product && vuln.product.length"
            :data="vuln.product"
            size="small"
            border
            class="affected-table"
          >
            <el-table-column prop="vendor" :label="$t('vulnForm.fields.vendor')" min-width="140">
              <template #default="{ row }">{{ row.vendor || '—' }}</template>
            </el-table-column>
            <el-table-column prop="product" :label="$t('vulnForm.fields.product')" min-width="160">
              <template #default="{ row }">{{ row.product || '—' }}</template>
            </el-table-column>
            <el-table-column :label="$t('vulnDetail.versionRange')" min-width="220">
              <template #default="{ row }">
                <code v-if="formatVersionRange(row) !== '—'" class="version-cell">{{ formatVersionRange(row) }}</code>
                <span v-else class="placeholder">—</span>
              </template>
            </el-table-column>
          </el-table>
          <p v-else class="no-data">{{ $t('vulnDetail.noProducts') }}</p>
        </section>

        <!-- 修复建议 -->
        <section class="detail-section">
          <header class="section-head">
            <h3 class="section-title"><i class="title-bar" />{{ $t('vulnDetail.sections.remediation') }}</h3>
          </header>
          <div class="remediation-grid">
            <div class="remediation-card mitigation">
              <div class="remediation-head">
                <el-icon><Cpu /></el-icon>
                <span>{{ $t('vulnForm.fields.patch') }}</span>
              </div>
              <MarkdownRenderer v-if="vuln.remediation?.mitigation" :content="vuln.remediation.mitigation" class="prose" />
              <p v-else class="no-data">{{ $t('vulnDetail.noPatch') }}</p>
            </div>
            <div class="remediation-card workaround">
              <div class="remediation-head">
                <el-icon><Tools /></el-icon>
                <span>{{ $t('vulnForm.fields.workaround') }}</span>
              </div>
              <MarkdownRenderer v-if="vuln.remediation?.workaround" :content="vuln.remediation.workaround" class="prose" />
              <p v-else class="no-data">{{ $t('vulnDetail.noWorkaround') }}</p>
            </div>
          </div>
        </section>

        <!-- 参考链接 -->
        <section class="detail-section">
          <header class="section-head">
            <h3 class="section-title"><i class="title-bar" />{{ $t('vulnDetail.sections.references') }}</h3>
            <span v-if="vuln.reference?.length" class="section-count">{{ $t('vulnDetail.refCount', { count: vuln.reference.length }) }}</span>
          </header>
          <div v-if="vuln.reference && vuln.reference.length" class="ref-list">
            <a
              v-for="(ref, i) in vuln.reference"
              :key="i"
              :href="ref.url"
              target="_blank"
              rel="noopener noreferrer"
              class="ref-link"
            >
              <el-icon class="ref-icon"><Link /></el-icon>
              <span class="ref-label">{{ ref.label || ref.url }}</span>
              <span class="ref-host">{{ hostOf(ref.url) }}</span>
            </a>
          </div>
          <p v-else class="no-data">{{ $t('vulnDetail.noReferences') }}</p>
        </section>

        <!-- 关联 POC 清单 -->
        <section class="detail-section">
          <header class="section-head">
            <h3 class="section-title"><i class="title-bar" />{{ $t('vulnDetail.sections.relatedPoc') }}</h3>
            <span v-if="vuln.pocs?.length" class="section-count">{{ $t('vulnDetail.pocCount', { count: vuln.pocs.length }) }}</span>
          </header>
          <div v-if="vuln.pocs?.length" class="poc-list">
            <div
              v-for="poc in vuln.pocs"
              :key="poc.id"
              class="poc-list-item"
              @click="$router.push(`/pocs/${poc.id}`)"
            >
              <div class="poc-item-left">
                <span class="poc-item-name">{{ poc.name }}</span>
                <span v-if="poc.title" class="poc-item-title">{{ poc.title }}</span>
              </div>
              <div class="poc-item-right">
                <SeverityBadge v-if="poc.severity" :severity="poc.severity" />
                <span class="poc-item-meta">{{ poc.source }} · {{ poc.format }}</span>
              </div>
            </div>
          </div>
          <p v-else class="no-data">{{ $t('vulnDetail.noRelatedPoc') }}</p>
        </section>
      </div>
    </div>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model:visible="deleteVisible"
      :title="$t('common.title.deleteConfirm')"
      :message="$t('vulnDetail.deleteConfirm', { cve: vuln?.cve_id ?? '' })"
      type="danger"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Back, CopyDocument, Cpu, Delete, Edit, Link, Tools } from '@element-plus/icons-vue'
import { deleteVuln, getVuln } from '@/api/vuln'
import { usePermission } from '@/composables/usePermission'
import { copyToClipboard, formatDate } from '@/utils/format'
import { parseCvssVector } from '@/utils/cvss'
import PageHeader from '@/components/common/PageHeader.vue'
import SeverityBadge from '@/components/common/SeverityBadge.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import MarkdownRenderer from '@/components/poc/MarkdownRenderer.vue'
import type { AffectedProduct, PocBrief, VulnItem } from '@/types/vuln'

const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const { t } = useI18n()

const loading = ref(true)
const vuln = ref<VulnItem | null>(null)
const deleteVisible = ref(false)
const pocLoading = ref(false)

const cvssVector = computed(() => parseCvssVector(vuln.value?.cvss_metrics))

/** 加载 CVE 详情。 */
async function loadData() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    vuln.value = await getVuln(id)
  } catch {
    router.push('/vulns')
  } finally {
    loading.value = false
  }
}

/** 跳转到关联 POC 的详情页（取首个关联 POC；无关联则提示）。 */
function goRelatedPoc() {
  if (!vuln.value) return
  if (!vuln.value.pocs?.length) {
    ElMessage.info(t('vulnDetail.noRelatedPoc'))
    return
  }
  router.push(`/pocs/${vuln.value.pocs[0].id}`)
}

/** 打开删除确认框。 */
function handleDelete() {
  deleteVisible.value = true
}

/** 跳转到 CVE 编辑页。 */
function goEdit() {
  if (vuln.value) router.push(`/vulns/${vuln.value.id}/edit`)
}

/** 确认删除，成功后返回列表。 */
async function confirmDelete() {
  deleteVisible.value = false
  if (!vuln.value) return
  try {
    await deleteVuln(vuln.value.id)
    ElMessage.success(t('common.message.deleteSuccess'))
    router.push('/vulns')
  } catch {
    // 错误已由拦截器统一提示
  }
}

/** 复制 CVSS 向量到剪贴板。 */
async function copyVector() {
  if (!vuln.value?.cvss_metrics) return
  await copyToClipboard(vuln.value.cvss_metrics)
  ElMessage.success(t('vulnDetail.copiedVector'))
}

/** 将受影响产品条目格式化为版本区间文本。 */
function formatVersionRange(row: AffectedProduct): string {
  const parts: string[] = []
  if (row.version) parts.push(row.version)
  if (row.version_start || row.version_end) {
    const start = row.version_start
      ? `${row.version_start_type === 'excluding' ? '(' : '['}${row.version_start}`
      : ''
    const end = row.version_end ? `${row.version_end}${row.version_end_type === 'excluding' ? ')' : ']'}` : ''
    if (start && end) parts.push(`${start}, ${end}`)
    else if (start) parts.push(`${start},`)
    else if (end) parts.push(`, ${end}`)
  }
  return parts.length ? parts.join('  ') : '—'
}

/** 从 URL 提取 host，用于参考链接的副标注。 */
function hostOf(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return url
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.vuln-detail-view {
  height: 100%;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

/* ── 顶部指标条 ── */
.metric-strip {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-md $spacing-xl;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;

  &.cvss-metric {
    flex-direction: row;
    align-items: center;
    gap: $spacing-sm;
  }
}

.metric-label {
  font-size: 12px;
  color: $text-disabled;
  letter-spacing: 0.02em;
}

.metric-value {
  font-size: $font-body;
  color: $text-primary;
  font-weight: 500;

  &.mono {
    font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
    font-size: $font-caption;
    font-weight: 400;
    color: $text-secondary;
  }
}

.metric-divider {
  width: 1px;
  align-self: stretch;
  background: $border-subtle;
}

/* CVSS 大号评分 */
.cvss-num {
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;

  &.critical { color: var(--vs-critical); }
  &.high { color: var(--vs-high); }
  &.medium { color: var(--vs-medium); }
  &.low { color: var(--vs-low); }
  &.info { color: var(--vs-info); }
}

.cvss-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cvss-ver {
  font-size: 11px;
  color: $text-disabled;
}

.placeholder {
  color: $text-disabled;
}

/* ── 通用分区卡片 ── */
.sections {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.detail-section {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-lg $spacing-xl;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
}

.section-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  margin: 0;
}

.title-bar {
  display: inline-block;
  width: 3px;
  height: 1em;
  border-radius: 2px;
  background: var(--vs-accent);
}

.section-count {
  font-size: $font-caption;
  color: $text-disabled;
}

/* ── CVSS 向量 ── */
.vector-raw {
  display: block;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: $font-caption;
  color: $text-secondary;
  background: $bg-tertiary;
  border: 1px solid $border-subtle;
  border-radius: $radius-sm;
  padding: $spacing-sm $spacing-md;
  margin-bottom: $spacing-md;
  word-break: break-all;
}

.vector-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.vector-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;

  .chip-key { color: $text-secondary; }
  .chip-sep { color: $text-disabled; margin: 0 2px; }
  .chip-val { color: $text-primary; font-weight: 500; }
}

/* ── 受影响产品表 ── */
.affected-table {
  :deep(.el-table__cell) {
    padding: 6px 0;
  }
}

.version-cell {
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: $font-caption;
  color: $text-secondary;
}

/* ── 修复建议卡片 ── */
.remediation-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-md;
}

.remediation-card {
  background: $bg-tertiary;
  border: 1px solid $border-subtle;
  border-left: 3px solid var(--vs-info);
  border-radius: $radius-sm;
  padding: $spacing-md $spacing-lg;
  transition: border-color $transition-fast;

  &.mitigation { border-left-color: var(--vs-active); }
  &.workaround { border-left-color: var(--vs-high); }

  &:hover {
    border-color: $border-color;
  }

  .prose :deep(.markdown-body) {
    font-size: $font-caption;
  }
}

.remediation-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: $font-caption;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: $spacing-sm;

  .mitigation & { color: var(--vs-active); }
  .workaround & { color: var(--vs-high); }
}

/* ── 参考链接 ── */
.ref-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.ref-link {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-sm;
  color: $text-primary;
  font-size: $font-body;
  background: transparent;
  border: 1px solid transparent;
  transition: all $transition-fast;

  &:hover {
    background: $bg-tertiary;
    border-color: $border-subtle;
    color: var(--vs-accent);
  }
}

.ref-icon {
  flex-shrink: 0;
  font-size: 14px;
  color: var(--vs-accent);
}

.ref-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ref-host {
  flex-shrink: 0;
  font-size: 11px;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  color: $text-disabled;
}

.no-data {
  color: $text-disabled;
  font-size: $font-body;
  margin: 0;
  padding: $spacing-sm 0;
}

/* 描述/正文阅读体验 */
.prose :deep(.markdown-body) {
  font-size: $font-body;
}

/* ── 关联 POC 清单 ── */
.poc-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid $border-subtle;
  border-radius: $radius-sm;
  overflow: hidden;
}

.poc-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  padding: $spacing-sm $spacing-md;
  cursor: pointer;
  transition: background $transition-fast;
  border-bottom: 1px solid $border-subtle;

  &:last-child { border-bottom: none; }

  &:hover {
    background: $bg-tertiary;
  }
}

.poc-item-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.poc-item-name {
  font-size: $font-body;
  font-weight: 500;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.poc-item-title {
  font-size: $font-caption;
  color: $text-secondary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.poc-item-right {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-shrink: 0;
}

.poc-item-meta {
  font-size: 11px;
  color: $text-disabled;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
}
</style>
