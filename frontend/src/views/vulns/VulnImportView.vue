<template>
  <div class="cve-import-view">
    <PageHeader :title="$t('nav.vulnImport')" :description="$t('vulnImport.headerDesc')">
      <template #actions>
        <el-button :icon="Document" @click="templateDrawer = true">{{ $t('vulnImport.viewTemplates') }}</el-button>
        <el-button v-if="result" :icon="Refresh" @click="resetImport">{{ $t('vulnImport.continueImport') }}</el-button>
        <el-button type="primary" :icon="Warning" @click="$router.push('/vulns')">{{ $t('vulnImport.viewList') }}</el-button>
      </template>
    </PageHeader>

    <div class="import-layout">
      <!-- 左侧：导入面板 -->
      <div class="import-panel">
        <div class="mode-tabs">
          <button class="mode-tab" :class="{ active: mode === 'file' }" @click="mode = 'file'">
            <el-icon :size="18"><UploadFilled /></el-icon>
            <span>{{ $t('vulnImport.mode.file') }}</span>
          </button>
          <button class="mode-tab" :class="{ active: mode === 'paste' }" @click="mode = 'paste'">
            <el-icon :size="18"><EditPen /></el-icon>
            <span>{{ $t('vulnImport.mode.paste') }}</span>
          </button>
        </div>

        <!-- 文件上传模式 -->
        <div v-show="mode === 'file'" class="mode-body">
          <el-upload
            ref="uploadRef"
            drag
            multiple
            :auto-upload="false"
            :show-file-list="false"
            accept=".json,.jsonl,.yaml,.yml,.md,.markdown,.txt"
            :on-change="handleFileChange"
            class="upload-area"
          >
            <div class="upload-content">
              <div class="upload-icon-wrap">
                <el-icon class="upload-icon" :size="48"><UploadFilled /></el-icon>
              </div>
              <div class="upload-title">{{ $t('vulnImport.upload.title') }}</div>
              <div class="upload-desc">{{ $t('vulnImport.upload.desc') }}</div>
              <div class="upload-formats">
                <span class="format-group"><span class="format-label">JSON</span><span class="format-ext">json</span></span>
                <span class="format-group"><span class="format-label">JSONL</span><span class="format-ext">jsonl</span></span>
                <span class="format-group"><span class="format-label">YAML</span><span class="format-ext">yaml / yml</span></span>
                <span class="format-group"><span class="format-label">Markdown</span><span class="format-ext">md</span></span>
              </div>
            </div>
          </el-upload>

          <transition-group name="fade" tag="div" class="file-list" v-if="selectedFiles.length">
            <div v-for="(f, i) in selectedFiles" :key="`${f.name}-${f.lastModified}-${i}`" class="file-card">
              <div class="file-icon"><el-icon :size="28"><Document /></el-icon></div>
              <div class="file-info">
                <span class="file-name">{{ f.name }}</span>
                <span class="file-size">{{ formatFileSize(f.size) }}</span>
              </div>
              <div class="file-format">
                <span class="detect-badge">{{ detectFormatFromName(f.name) }}</span>
              </div>
              <el-button text type="danger" :icon="Close" @click="removeFile(i)" />
            </div>
          </transition-group>

          <div v-if="selectedFiles.length > 1" class="batch-summary">
            <el-icon :size="14"><InfoFilled /></el-icon>
            <span>{{ $t('vulnImport.batchSummary', { count: selectedFiles.length }) }}</span>
            <el-button text size="small" type="primary" @click="clearFiles">{{ $t('vulnImport.clearAll') }}</el-button>
          </div>
        </div>

        <!-- 粘贴文本模式 -->
        <div v-show="mode === 'paste'" class="mode-body">
          <div class="paste-area">
            <el-input
              v-model="pastedContent"
              type="textarea"
              :rows="12"
              :placeholder="$t('vulnImport.paste.placeholder')"
              class="paste-textarea"
            />
            <div class="paste-hint">
              <el-icon :size="14"><InfoFilled /></el-icon>
              <span>{{ $t('vulnImport.paste.hint') }}</span>
            </div>
          </div>
        </div>

        <!-- 导入按钮 -->
        <button
          class="import-action-btn"
          :class="{ disabled: !hasContent, loading: importing }"
          :disabled="!hasContent || importing"
          @click="handleImport"
        >
          <span v-if="importing" class="btn-spinner" />
          <el-icon v-else :size="18"><Upload /></el-icon>
          <span>{{ importing ? $t('vulnImport.import.running') : $t('vulnImport.import.action') }}</span>
        </button>
      </div>

      <!-- 右侧：结果面板 -->
      <transition name="slide-fade" mode="out-in">
        <div v-if="result" class="result-panel">
          <div class="result-header">
            <h3 class="result-panel-title">{{ $t('vulnImport.result.title') }}</h3>
          </div>

          <div class="result-ring">
            <svg viewBox="0 0 120 120" class="ring-svg">
              <circle cx="60" cy="60" r="52" class="ring-bg" />
              <circle
                cx="60" cy="60" r="52"
                class="ring-fill"
                :style="{ strokeDasharray: circumference, strokeDashoffset: ringOffset }"
              />
            </svg>
            <div class="ring-center">
              <span class="ring-total">{{ result.total }}</span>
              <span class="ring-label">{{ $t('vulnImport.result.total') }}</span>
            </div>
          </div>

          <div class="result-breakdown">
            <div class="breakdown-item created">
              <div class="breakdown-bar" :style="{ width: barPercent(result.created, result.total) }" />
              <div class="breakdown-info">
                <span class="breakdown-value">{{ result.created }}</span>
                <span class="breakdown-label">{{ $t('vulnImport.result.created') }}</span>
              </div>
            </div>
            <div class="breakdown-item updated">
              <div class="breakdown-bar" :style="{ width: barPercent(result.updated, result.total) }" />
              <div class="breakdown-info">
                <span class="breakdown-value">{{ result.updated }}</span>
                <span class="breakdown-label">{{ $t('vulnImport.result.updated') }}</span>
              </div>
            </div>
            <div class="breakdown-item skipped">
              <div class="breakdown-bar" :style="{ width: barPercent(result.skipped, result.total) }" />
              <div class="breakdown-info">
                <span class="breakdown-value">{{ result.skipped }}</span>
                <span class="breakdown-label">{{ $t('vulnImport.result.skipped') }}</span>
              </div>
            </div>
            <div class="breakdown-item failed">
              <div class="breakdown-bar" :style="{ width: barPercent(result.failed.length, result.total) }" />
              <div class="breakdown-info">
                <span class="breakdown-value">{{ result.failed.length }}</span>
                <span class="breakdown-label">{{ $t('vulnImport.result.failed') }}</span>
              </div>
            </div>
          </div>

          <div v-if="result.failed.length" class="fail-section">
            <div class="fail-header">
              <el-icon :size="16"><WarningFilled /></el-icon>
              <span>{{ $t('vulnImport.result.failDetail') }}</span>
            </div>
            <div class="fail-list">
              <div v-for="(f, i) in result.failed" :key="i" class="fail-item">
                <span class="fail-index">{{ i + 1 }}</span>
                <span class="fail-name">{{ f.name || $t('vulnImport.result.unknownItem') }}</span>
                <span class="fail-msg">{{ f.error }}</span>
              </div>
            </div>
          </div>

          <div v-if="result.success > 0" class="result-success-msg">
            <el-icon :size="16" class="check-icon"><CircleCheck /></el-icon>
            <span>{{ $t('vulnImport.result.successMsg', { success: result.success, created: result.created, updated: result.updated }) }}</span>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="result-panel empty">
          <div class="empty-result">
            <el-icon :size="48" class="empty-icon"><Upload /></el-icon>
            <h3 class="empty-title">{{ $t('vulnImport.empty.title') }}</h3>
            <p class="empty-desc">{{ $t('vulnImport.empty.desc') }}</p>
            <div class="empty-features">
              <div class="feature-item"><span class="feature-dot" /><span>{{ $t('vulnImport.empty.features.auto') }}</span></div>
              <div class="feature-item"><span class="feature-dot" /><span>{{ $t('vulnImport.empty.features.dedup') }}</span></div>
              <div class="feature-item"><span class="feature-dot" /><span>{{ $t('vulnImport.empty.features.batch') }}</span></div>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- 模板抽屉 -->
    <el-drawer v-model="templateDrawer" :title="$t('vulnImport.template.drawerTitle')" size="640px" direction="rtl">
      <el-tabs v-model="activeTemplate">
        <el-tab-pane v-for="t in CVE_TEMPLATE_LIST" :key="t.key" :label="t.label" :name="t.key">
          <div class="template-bar">
            <span class="template-ext">{{ t.ext }}</span>
            <el-button text size="small" :icon="CopyDocument" @click="copyTemplate(t.content)">{{ $t('vulnImport.template.copy') }}</el-button>
          </div>
          <pre class="template-code"><code>{{ t.content }}</code></pre>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  UploadFilled, EditPen, Document, Close, Upload, Refresh,
  InfoFilled, WarningFilled, CircleCheck, Warning, CopyDocument,
} from '@element-plus/icons-vue'
import { importVulns } from '@/api/vuln'
import { copyToClipboard } from '@/utils/format'
import { CVE_TEMPLATE_LIST } from '@/utils/cveTemplates'
import PageHeader from '@/components/common/PageHeader.vue'
import type { VulnImportResult } from '@/types/vuln'

const { t } = useI18n()
const uploadRef = ref()

const mode = ref<'file' | 'paste'>('file')
const selectedFiles = ref<File[]>([])
const pastedContent = ref('')
const importing = ref(false)
const result = ref<VulnImportResult | null>(null)
const templateDrawer = ref(false)
const activeTemplate = ref<'json' | 'jsonl' | 'yaml' | 'markdown'>('json')

const hasContent = computed(() => selectedFiles.value.length > 0 || !!pastedContent.value.trim())

const circumference = 2 * Math.PI * 52

const ringOffset = computed(() => {
  if (!result.value || result.value.total === 0) return circumference
  const ratio = result.value.success / result.value.total
  return circumference * (1 - ratio)
})

function barPercent(value: number, total: number): string {
  if (total === 0) return '0%'
  return `${(value / total) * 100}%`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function detectFormatFromName(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase()
  const map: Record<string, string> = {
    json: 'JSON',
    jsonl: 'JSONL',
    yaml: 'YAML',
    yml: 'YAML',
    md: 'Markdown',
    markdown: 'Markdown',
    txt: t('vulnImport.format.txt'),
  }
  return map[ext || ''] || t('vulnImport.detectUnknown')
}

function handleFileChange(uploadFile: { raw: File }) {
  if (mode.value === 'paste') mode.value = 'file'
  const file = uploadFile.raw
  if (!file) return
  const exists = selectedFiles.value.some(
    (f, i) => f.name === file.name && f.size === file.size && i === selectedFiles.value.length - 1,
  )
  if (!exists) selectedFiles.value.push(file)
  pastedContent.value = ''
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
}

function clearFiles() {
  selectedFiles.value = []
  if (uploadRef.value) uploadRef.value.clearFiles()
}

watch(mode, (m) => {
  result.value = null
  if (m === 'file') pastedContent.value = ''
  else clearFiles()
})

async function handleImport() {
  importing.value = true
  result.value = null
  try {
    const formData = new FormData()
    if (selectedFiles.value.length) {
      selectedFiles.value.forEach((f) => formData.append('files', f))
    } else if (pastedContent.value.trim()) {
      formData.append('content', pastedContent.value)
    }
    result.value = await importVulns(formData)
  } catch {
    // 错误已由拦截器统一提示
  } finally {
    importing.value = false
  }
}

function resetImport() {
  clearFiles()
  pastedContent.value = ''
  result.value = null
}

async function copyTemplate(content: string) {
  await copyToClipboard(content)
  ElMessage.success(t('vulnImport.template.copied'))
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.cve-import-view {
  max-width: 1100px;
  margin: 0 auto;
  height: 100%;
}

.import-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-xl;
  height: calc(100vh - 180px);
  align-items: stretch;
}

// ── 左侧面板 ──────────────────────────────────────────────────
.import-panel {
  display: flex;
  flex-direction: column;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  overflow: hidden;
}

.mode-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid $border-color;
  flex-shrink: 0;
}

.mode-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 16px;
  background: transparent;
  border: none;
  color: $text-secondary;
  font-size: $font-body;
  font-family: inherit;
  cursor: pointer;
  transition: all $transition-fast;
  position: relative;

  &:hover {
    color: $text-primary;
    background: rgba($accent, 0.04);
  }

  &.active {
    color: $accent;
    background: rgba($accent, 0.08);

    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 20%;
      right: 20%;
      height: 2px;
      background: $accent;
      border-radius: 1px;
    }
  }
}

.mode-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: $spacing-xl;
  overflow-y: auto;
}

.upload-area {
  width: 100%;
  flex-shrink: 0;

  :deep(.el-upload-dragger) {
    width: 100%;
    background: $bg-tertiary;
    border: 1px dashed $border-color;
    border-radius: 8px;
    padding: 36px 20px;
    transition: all $transition-fast;

    &:hover {
      border-color: $accent;
      background: rgba($accent, 0.04);
    }

    &.is-dragover {
      border-color: $accent;
      background: rgba($accent, 0.08);
    }
  }
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon-wrap {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba($accent, 0.08);
  border-radius: 50%;
  margin-bottom: 4px;
}

.upload-icon { color: $accent; }
.upload-title { font-size: 15px; color: $text-primary; font-weight: 500; }
.upload-desc { font-size: $font-body; color: $text-secondary; }

.upload-formats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 8px;
}

.format-group {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  font-size: $font-caption;
  background: rgba($accent, 0.06);
  border: 1px solid rgba($accent, 0.12);
  border-radius: 12px;
}

.format-label { color: $text-secondary; font-weight: 500; }
.format-ext {
  color: $text-disabled;
  font-size: 11px;
  padding: 0 2px;
  background: rgba($accent, 0.08);
  border-radius: 3px;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: $spacing-lg;
  max-height: 280px;
  overflow-y: auto;
  padding-right: 4px;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba($accent, 0.06);
  border: 1px solid rgba($accent, 0.15);
  border-radius: 8px;
}

.file-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba($accent, 0.1);
  border-radius: 8px;
  color: $accent;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.file-name {
  font-size: $font-body;
  color: $text-primary;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size { font-size: $font-caption; color: $text-disabled; }
.file-format { flex-shrink: 0; }

.batch-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: $spacing-md;
  padding: 8px 12px;
  font-size: $font-caption;
  color: $text-secondary;
  background: rgba($info, 0.06);
  border: 1px solid rgba($info, 0.15);
  border-radius: 6px;

  .el-button { margin-left: auto; }
}

.detect-badge {
  padding: 2px 10px;
  font-size: $font-caption;
  color: $accent;
  background: rgba($accent, 0.1);
  border: 1px solid rgba($accent, 0.2);
  border-radius: 4px;
  white-space: nowrap;
}

.paste-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.paste-textarea {
  flex: 1;
  min-height: 0;

  :deep(.el-textarea) { height: 100%; }

  :deep(textarea) {
    height: 100%;
    min-height: 240px;
    font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 13px;
    line-height: 1.6;
    background: $bg-tertiary;
    border-color: $border-color;

    &:focus { border-color: $accent; }

    &::placeholder {
      color: $text-disabled;
      font-family: $font-family;
      font-size: $font-body;
    }
  }
}

.paste-hint {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: $font-caption;
  color: $text-disabled;
}

.import-action-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px 16px;
  border: none;
  background: $accent;
  color: $text-inverse;
  font-size: 15px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all $transition-fast;
  letter-spacing: 0.3px;

  &:hover:not(.disabled) { background: $accent-hover; }

  &.disabled {
    background: $bg-tertiary;
    color: $text-disabled;
    cursor: not-allowed;
  }

  &.loading {
    background: $bg-tertiary;
    color: $text-secondary;
    cursor: wait;
  }
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid $text-disabled;
  border-top-color: $accent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

// ── 右侧结果面板 ──────────────────────────────────────────────
.result-panel {
  display: flex;
  flex-direction: column;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-xl;
  overflow-y: auto;

  &.empty {
    justify-content: center;
    align-items: center;
  }
}

.result-header { margin-bottom: $spacing-xl; }
.result-panel-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  margin: 0;
}

.result-ring {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto $spacing-xl;
}

.ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg { fill: none; stroke: $bg-tertiary; stroke-width: 8; }
.ring-fill {
  fill: none;
  stroke: $active;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.8s ease;
}

.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring-total {
  font-size: 28px;
  font-weight: 700;
  color: $text-primary;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.ring-label {
  font-size: $font-caption;
  color: $text-disabled;
  margin-top: 2px;
}

.result-breakdown {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: $spacing-xl;
}

.breakdown-item {
  position: relative;
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  overflow: hidden;

  &.created { background: rgba($active, 0.06); }
  &.updated { background: rgba($accent, 0.06); }
  &.skipped { background: rgba($medium, 0.06); }
  &.failed { background: rgba($critical, 0.06); }
}

.breakdown-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  transition: width 0.6s ease;
  border-radius: 6px;

  .created & { background: rgba($active, 0.12); }
  .updated & { background: rgba($accent, 0.12); }
  .skipped & { background: rgba($medium, 0.12); }
  .failed & { background: rgba($critical, 0.12); }
}

.breakdown-info {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.breakdown-value {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;

  .created & { color: $active; }
  .updated & { color: $accent; }
  .skipped & { color: $medium; }
  .failed & { color: $critical; }
}

.breakdown-label {
  font-size: $font-body;
  color: $text-secondary;
}

.fail-section { margin-bottom: $spacing-lg; }

.fail-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: $font-body;
  font-weight: 600;
  color: $critical;
  margin-bottom: $spacing-sm;
}

.fail-list {
  max-height: 160px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.fail-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid $border-subtle;
  font-size: $font-caption;
  line-height: 1.5;
}

.fail-index {
  width: 18px;
  flex-shrink: 0;
  color: $text-disabled;
  font-variant-numeric: tabular-nums;
}

.fail-name {
  width: 120px;
  flex-shrink: 0;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fail-msg {
  color: $critical;
  flex: 1;
}

.result-success-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba($active, 0.08);
  border: 1px solid rgba($active, 0.15);
  border-radius: 6px;
  font-size: $font-body;
  color: $active;
}

.check-icon { flex-shrink: 0; }

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: $spacing-xl 0;
}

.empty-icon {
  color: $text-disabled;
  margin-bottom: $spacing-lg;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: $text-secondary;
  margin: 0 0 $spacing-sm;
}

.empty-desc {
  font-size: $font-body;
  color: $text-disabled;
  margin: 0 0 $spacing-xl;
  max-width: 280px;
  line-height: 1.6;
}

.empty-features {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: $font-caption;
  color: $text-secondary;
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: $accent;
  opacity: 0.5;
}

// ── 模板抽屉 ──────────────────────────────────────────────────
.template-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-sm;
}

.template-ext {
  font-size: $font-caption;
  color: $text-disabled;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
}

.template-code {
  margin: 0;
  padding: $spacing-md;
  background: $bg-tertiary;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  overflow: auto;
  max-height: 60vh;

  code {
    font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 12.5px;
    line-height: 1.6;
    color: $text-secondary;
    white-space: pre;
  }
}

// ── 过渡动画 ───────────────────────────────────────────────────
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.fade-enter-active,
.fade-leave-active {
  transition: all 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
