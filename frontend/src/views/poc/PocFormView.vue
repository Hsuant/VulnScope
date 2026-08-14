<template>
  <div v-loading="loading" class="poc-form-view">
    <PageHeader :title="isEdit ? '编辑 POC' : '新建 POC'">
      <template #actions>
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :loading="saving" :icon="Check" @click="handleSave">保存</el-button>
      </template>
    </PageHeader>

    <div class="form-grid">
      <!-- 左列：表单 -->
      <div class="form-left">
        <div class="form-section">
          <h3 class="section-title">基本信息</h3>
          <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="left">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" placeholder="字母数字汉字开头，允许字母、数字、汉字、连字符和空格" :disabled="isEdit" />
            </el-form-item>
            <el-form-item label="标题" prop="title">
              <el-input v-model="form.title" placeholder="显示标题，如 Apache Struts2 S2-045 RCE" />
            </el-form-item>
            <el-form-item label="严重级别" prop="severity">
              <el-select v-model="form.severity" class="w-full">
                <el-option v-for="s in SEVERITY_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" class="w-full">
                <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="来源" prop="source">
              <el-select v-model="form.source" class="w-full">
                <el-option v-for="s in SOURCE_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="格式" prop="format">
              <el-select v-model="form.format" class="w-full">
                <el-option v-for="s in FORMAT_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="作者" prop="author">
              <el-input v-model="form.author" placeholder="作者名称" />
            </el-form-item>
            <el-form-item v-if="form.format === 'raw-script'" label="语言" prop="language">
              <el-input v-model="form.language" placeholder="脚本语言，如 python、go" />
            </el-form-item>
          </el-form>
        </div>

        <div class="form-section">
          <h3 class="section-title">关联信息</h3>
          <el-form label-width="80px" label-position="left">
            <el-form-item label="CVE 编号">
              <el-select
                v-model="form.cve_ids"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入 CVE 编号，回车添加"
                class="w-full"
              >
                <el-option v-for="cve in form.cve_ids" :key="cve" :label="cve" :value="cve" />
              </el-select>
            </el-form-item>
            <el-form-item label="CNVD 编号">
              <el-select
                v-model="form.cnvd_ids"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入 CNVD/CNNVD 编号，回车添加"
                class="w-full"
              >
                <el-option v-for="cnvd in form.cnvd_ids" :key="cnvd" :label="cnvd" :value="cnvd" />
              </el-select>
            </el-form-item>
            <el-form-item label="FOFA 语法">
              <el-input
                v-model="form.fofa_syntax"
                placeholder="资产探测 FOFA 语法，如 app=&quot;Apache-Struts2&quot;"
                clearable
              />
            </el-form-item>
            <el-form-item label="Shodan 语法">
              <el-input
                v-model="form.shodan_syntax"
                placeholder="资产探测 Shodan 语法，如 product:&quot;Apache Struts&quot;"
                clearable
              />
            </el-form-item>
            <el-form-item label="参考链接">
              <div class="reference-list w-full">
                <div
                  v-for="(ref, idx) in form.references"
                  :key="idx"
                  class="reference-row"
                >
                  <div class="ref-fields">
                    <el-input
                      v-model="ref.url"
                      size="small"
                      placeholder="参考链接 URL"
                      class="ref-url"
                    >
                      <template #prefix>
                        <el-icon><Link /></el-icon>
                      </template>
                    </el-input>
                    <el-input
                      v-model="ref.label"
                      size="small"
                      placeholder="标题（可选）"
                      class="ref-label"
                    />
                  </div>
                  <div class="ref-actions">
                    <el-button
                      text
                      size="small"
                      :icon="ref._verifying ? Loading : Link"
                      :class="{ 'ref-verified': ref._verified }"
                      :disabled="ref._verifying"
                      @click="verifyRef(idx)"
                    />
                    <el-button
                      text
                      type="danger"
                      :icon="Delete"
                      size="small"
                      @click="removeRef(idx)"
                    />
                  </div>
                </div>
                <el-button
                  text
                  type="primary"
                  :icon="Plus"
                  size="small"
                  class="mt-sm"
                  @click="addRef"
                >
                  添加参考链接
                </el-button>
              </div>
            </el-form-item>
            <el-form-item label="标签">
              <el-select
                v-model="form.tag_ids"
                multiple
                filterable
                placeholder="选择标签"
                class="w-full"
              >
                <el-option
                  v-for="tag in allTags"
                  :key="tag.id"
                  :label="`${tag.namespace}:${tag.name}`"
                  :value="tag.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="4"
                placeholder="漏洞描述信息"
              />
            </el-form-item>
          </el-form>
        </div>

        <div class="form-section">
          <h3 class="section-title">受影响版本</h3>
          <el-form label-width="80px" label-position="left">
            <div class="affected-list">
              <div
                v-for="(item, idx) in form.affected_versions"
                :key="idx"
                class="affected-row"
              >
                <div class="affected-fields">
                  <div class="affected-group">
                    <span class="affected-label">起始</span>
                    <el-select v-model="item.version_start_type" size="small" class="op-select">
                      <el-option label=">=" value=">=" />
                      <el-option label=">" value=">" />
                      <el-option label="任意" value="" />
                    </el-select>
                    <el-input
                      v-model="item.version_start"
                      size="small"
                      placeholder="如 1.0.0"
                      class="ver-input"
                    />
                  </div>
                  <div class="affected-group">
                    <span class="affected-label">截止</span>
                    <el-select v-model="item.version_end_type" size="small" class="op-select">
                      <el-option label="<=" value="<=" />
                      <el-option label="<" value="<" />
                      <el-option label="任意" value="" />
                    </el-select>
                    <el-input
                      v-model="item.version_end"
                      size="small"
                      placeholder="如 2.0.0"
                      class="ver-input"
                    />
                  </div>
                </div>
                <el-button
                  text
                  type="danger"
                  :icon="Delete"
                  size="small"
                  class="affected-remove"
                  @click="removeAffected(idx)"
                />
              </div>
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="addAffected">
              添加版本范围
            </el-button>
          </el-form>
        </div>
      </div>

      <!-- 右列：内容构建器 -->
      <div class="form-right">
        <div class="form-section editor-section">
          <div class="editor-header">
            <h3 class="section-title">POC 内容 *</h3>
            <div class="editor-tools">
              <el-tag size="small">{{ form.format }}</el-tag>
              <el-radio-group
                v-if="canBuild"
                v-model="editMode"
                size="small"
                class="mode-switch"
              >
                <el-radio-button value="builder">表单构建</el-radio-button>
                <el-radio-button value="source">源码</el-radio-button>
              </el-radio-group>
            </div>
          </div>

          <!-- 表单构建模式 -->
          <div v-if="canBuild && editMode === 'builder'" class="editor-container builder-container">
            <PocBuilder :state="builderState" />
            <div class="builder-actions">
              <el-button size="small" :icon="Refresh" @click="syncFromBuilder">同步到源码</el-button>
              <el-button size="small" :icon="Download" @click="editMode = 'source'">查看源码</el-button>
            </div>
          </div>

          <!-- 源码模式 -->
          <div v-else class="editor-container">
            <div v-if="canBuild" class="source-hint">
              <el-icon :size="14"><InfoFilled /></el-icon>
              <span>修改源码后切回「表单构建」将自动解析回填字段（高级语法可能无法完全还原）</span>
            </div>
            <textarea
              v-model="form.content"
              class="code-textarea"
              :placeholder="editorPlaceholder"
              spellcheck="false"
              @input="markSourceDirty"
            />
          </div>

          <div v-if="!canBuild" class="format-hint">
            <el-icon :size="14"><InfoFilled /></el-icon>
            <span>当前格式（{{ formatLabel }}）为脚本类，仅支持源码模式编辑</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Refresh, Download, InfoFilled, Delete, Plus, Link, Loading } from '@element-plus/icons-vue'
import { getPoc, createPoc, updatePoc, verifyUrl } from '@/api/poc'
import { listTags } from '@/api/tag'
import { SEVERITY_OPTIONS, STATUS_OPTIONS, SOURCE_OPTIONS, FORMAT_OPTIONS, FORMAT_MAP } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import PocBuilder from '@/components/poc/PocBuilder.vue'
import type { TagItem } from '@/types/tag'
import type { AffectedVersion, Reference } from '@/types/poc'
import {
  createEmptyState, generateContent, parseContent, canBuild as canBuildFormat,
  readBuilderMeta, type BuilderState,
} from '@/utils/pocBuilder'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const pocId = computed(() => Number(route.params.id))

const loading = ref(isEdit.value)
const saving = ref(false)
const formRef = ref()
const allTags = ref<TagItem[]>([])

// 表单构建器状态（结构化字段），与源码 content 双向同步
const builderState = reactive<BuilderState>(createEmptyState())
const editMode = ref<'builder' | 'source'>('builder')
const sourceDirty = ref(false) // 源码被手改过，切回 builder 时需重新解析

const form = reactive({
  name: '',
  title: '',
  severity: 'info',
  status: 'draft',
  source: 'manual',
  format: 'nuclei-yaml',
  author: '',
  language: '',
  description: '',
  content: '',
  cve_ids: [] as string[],
  cnvd_ids: [] as string[],
  references: [] as (Reference & { _verifying?: boolean; _verified?: boolean })[],
  fofa_syntax: '',
  shodan_syntax: '',
  tag_ids: [] as number[],
  affected_versions: [] as AffectedVersion[],
  extra_meta: {} as Record<string, any>,
})

const canBuild = computed(() => canBuildFormat(form.format))
const formatLabel = computed(() => FORMAT_MAP[form.format] || form.format)

const rules: Record<string, any> = {
  name: [
    { required: true, message: '请输入 POC 名称', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9一-龥][a-zA-Z0-9一-龥 -]*$/, message: '以字母、数字或汉字开头，仅允许字母、数字、汉字、连字符 "-" 和空格', trigger: 'blur' },
  ],
  severity: [{ required: true, message: '请选择严重级别', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const editorPlaceholder = computed(() => {
  const map: Record<string, string> = {
    'nuclei-yaml': `id: struts2-s2-045-rce

info:
  name: Apache Struts2 S2-045 RCE
  author: security-team
  severity: high
  description: "Apache Struts2 存在远程代码执行漏洞，攻击者可通过 Content-Type 标头执行任意命令"
  remediation: "升级至 Struts2 2.3.32 或 2.5.10.1 及以上版本"
  classification:
    cve-id:
      - CVE-2017-5638
    cwe-id:
      - CWE-917
    cvss-metrics: "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    cvss-score: 10.0
  tags: rce, struts2, apache, cve-2017-5638, oss

http:
  - method: GET
    path:
      - "{{BaseURL}}"
    headers:
      Content-Type: "%{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse'].addHeader('X-Check','vuln')}.multipart/form-data"
    matchers:
      - type: word
        words:
          - "X-Check: vuln"
        part: header`,
    pocsuite3: `from pocsuite3.api import POCBase, register_poc
from pocsuite3.api import requests
from pocsuite3.lib.core.enums import VUL_TYPE


class ExamplePOC(POCBase):
    """示例 POC — 请替换为实际漏洞逻辑"""
    vulID = "CVE-2017-5638"
    version = 1.0
    author = "security-team"
    vulDate = "2017-03-07"
    appName = "Apache Struts2"
    appVersion = "2.3.5 - 2.3.31"
    appPowerLink = "https://struts.apache.org"
    vulType = VUL_TYPE.CODE_EXECUTION

    def _attack(self):
        return self._verify()

    def _verify(self):
        headers = {
            "Content-Type": "%{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse']
            .addHeader('X-Check','vuln')}.multipart/form-data"
        }
        resp = self._request(self.url, headers=headers)
        return self.parse_response(resp)`,
    'json': `{
  "name": "thinkphp5-rce",
  "title": "ThinkPHP 5 远程代码执行漏洞",
  "author": "security-team",
  "severity": "high",
  "description": "ThinkPHP 5 框架存在远程代码执行漏洞，攻击者可通过构造特制请求执行任意代码",
  "vulnerabilities": [
    "CVE-2018-20062"
  ],
  "tags": ["rce", "thinkphp", "php"],
  "request": {
    "method": "POST",
    "path": "/index.php?s=/Index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=id"
  },
  "response": {
    "check": "uid="
  }
}`,
    'raw-script': '#!/usr/bin/env python3\n# 原始脚本/模板内容\n# 支持任意语言，language 字段标注脚本类型\n\ndef verify(target: str) -> dict:\n    """POC 验证函数"""\n    result = {"vulnerable": False}\n    # 在此编写验证逻辑\n    return result',
  }
  return map[form.format] || '输入 POC 内容...'
})

async function loadData() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const poc = await getPoc(pocId.value)
    form.name = poc.name
    form.title = poc.title || ''
    form.severity = poc.severity
    form.status = poc.status
    form.source = poc.source
    form.format = poc.format
    form.author = poc.author || ''
    form.language = poc.language || ''
    form.description = poc.description || ''
    form.content = poc.content
    form.cve_ids = poc.cve_ids || []
    form.cnvd_ids = poc.cnvd_ids || []
    form.references = (poc.references || []).map(r => ({ ...r }))
    form.fofa_syntax = poc.fofa_syntax || ''
    form.shodan_syntax = poc.shodan_syntax || ''
    form.tag_ids = poc.tags?.map(t => t.id) || []
    form.affected_versions = (poc.affected_versions || []).map(v => ({ ...v }))
    form.extra_meta = poc.extra_meta || {}

    // 回填构建器状态：优先从 extra_meta.builder 精确恢复，否则从 content 解析
    const saved = readBuilderMeta(form.extra_meta)
    if (saved) {
      Object.assign(builderState, saved)
    } else if (canBuild.value && form.content) {
      Object.assign(builderState, parseContent(form.content, form.format))
    }
    editMode.value = canBuild.value ? 'builder' : 'source'
  } catch {
    router.push('/pocs')
  } finally {
    loading.value = false
  }
}

// 构建 context（元数据 + 协议状态），用于生成 content
function buildContext() {
  return {
    name: form.name || 'poc-template',
    title: form.title || undefined,
    author: form.author || undefined,
    severity: form.severity,
    description: form.description || undefined,
    cveIds: form.cve_ids,
    tagNames: allTags.value.filter((t) => form.tag_ids.includes(t.id)).map((t) => t.name),
    format: form.format,
    language: form.language || undefined,
    source: form.source,
    references: form.references.length ? form.references.map((r) => ({ url: r.url, label: r.label })) : undefined,
    fofaSyntax: form.fofa_syntax || undefined,
    shodanSyntax: form.shodan_syntax || undefined,
    affectedVersions: form.affected_versions.length ? form.affected_versions : undefined,
    state: builderState,
  }
}

// 把结构化字段同步到源码 content
function syncFromBuilder() {
  if (!canBuild.value) return
  form.content = generateContent(buildContext())
  sourceDirty.value = false
  ElMessage.success('已同步到源码')
}

function markSourceDirty() {
  sourceDirty.value = true
}

// 切到表单构建模式时，若源码被改过则解析回填
watch(editMode, (mode) => {
  if (mode === 'builder' && canBuild.value && sourceDirty.value && form.content) {
    Object.assign(builderState, parseContent(form.content, form.format))
    sourceDirty.value = false
  }
})

// 格式切换：非可构建格式强制源码模式；切到可构建格式时尝试解析现有 content
watch(() => form.format, (fmt) => {
  if (!canBuildFormat(fmt)) {
    editMode.value = 'source'
  } else {
    if (editMode.value === 'source' && form.content) {
      Object.assign(builderState, parseContent(form.content, fmt))
    }
    if (editMode.value !== 'source') editMode.value = 'builder'
  }
})

// 表单构建模式下，结构字段变化时实时生成 content（保持单一数据源）
watch(
  () => JSON.stringify({ ...builderState, name: form.name, title: form.title, author: form.author, severity: form.severity, description: form.description, cve_ids: form.cve_ids, tag_ids: form.tag_ids, source: form.source, format: form.format, references: form.references, fofa_syntax: form.fofa_syntax, shodan_syntax: form.shodan_syntax, affected_versions: form.affected_versions }),
  () => {
    if (canBuild.value && editMode.value === 'builder') {
      form.content = generateContent(buildContext())
      sourceDirty.value = false
    }
  },
)

async function loadTags() {
  try {
    const res = await listTags({ page_size: 200 })
    allTags.value = res.items
  } catch {
    // silent
  }
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  // 构建模式下，保存前确保 content 已由结构字段生成
  if (canBuild.value && editMode.value === 'builder') {
    form.content = generateContent(buildContext())
  }

  if (!form.content.trim()) {
    ElMessage.warning('请填写 POC 内容（请求/匹配器至少一项）')
    return
  }

  // 完整性校验：构建模式下需至少一条匹配器且非空
  if (canBuild.value && editMode.value === 'builder') {
    const hasMatcher = builderState.matchers.some(
      (m) => (m.type === 'status' ? m.status.length > 0 : m.words.some((w) => w.trim() !== '')),
    )
    if (!hasMatcher) {
      ElMessage.warning('请至少添加一条有效的匹配规则（关键词/状态码/DSL）')
      return
    }
    const protoOk =
      (builderState.protocol === 'http' && builderState.http.paths.some((p) => p.trim() !== '')) ||
      (builderState.protocol === 'tcp' && (builderState.tcp.inputs.some((i) => i.trim() !== '') || builderState.tcp.port.trim() !== '')) ||
      (builderState.protocol === 'network' && (builderState.network.inputs.some((i) => i.trim() !== '') || builderState.network.port.trim() !== '')) ||
      (builderState.protocol === 'websocket' && builderState.websocket.url.trim() !== '') ||
      (builderState.protocol === 'dns' && builderState.dns.domains.some((d) => d.trim() !== ''))
    if (!protoOk) {
      ElMessage.warning('请填写当前协议下必要的请求字段')
      return
    }
  }

  // 持久化构建器状态到 extra_meta，保证编辑精确回填
  const extraMeta = canBuild.value
    ? { ...(form.extra_meta || {}), builder: JSON.parse(JSON.stringify(builderState)) }
    : (form.extra_meta || {})

  saving.value = true
  try {
    if (isEdit.value) {
      await updatePoc(pocId.value, {
        title: form.title || undefined,
        severity: form.severity,
        status: form.status,
        source: form.source,
        format: form.format,
        author: form.author || undefined,
        language: form.language || undefined,
        description: form.description || undefined,
        content: form.content,
        cve_ids: form.cve_ids,
        cnvd_ids: form.cnvd_ids,
        references: form.references.length ? form.references.map(r => ({ url: r.url, label: r.label })) : undefined,
        fofa_syntax: form.fofa_syntax,
        shodan_syntax: form.shodan_syntax,
        tag_ids: form.tag_ids,
        affected_versions: form.affected_versions.length ? form.affected_versions : undefined,
        extra_meta: extraMeta,
      })
      ElMessage.success('更新成功')
      router.push(`/pocs/${pocId.value}`)
    } else {
      const newPoc = await createPoc({
        name: form.name,
        title: form.title || undefined,
        severity: form.severity,
        status: form.status,
        source: form.source,
        format: form.format,
        author: form.author || undefined,
        language: form.language || undefined,
        description: form.description || undefined,
        content: form.content,
        cve_ids: form.cve_ids,
        cnvd_ids: form.cnvd_ids,
        references: form.references.length ? form.references.map(r => ({ url: r.url, label: r.label })) : undefined,
        fofa_syntax: form.fofa_syntax,
        shodan_syntax: form.shodan_syntax,
        tag_ids: form.tag_ids,
        affected_versions: form.affected_versions.length ? form.affected_versions : undefined,
        extra_meta: extraMeta,
      })
      ElMessage.success('创建成功')
      router.push(`/pocs/${newPoc.id}`)
    }
  } catch {
    // handled by interceptor
  } finally {
    saving.value = false
  }
}

function handleCancel() {
  if (isEdit.value) {
    router.push(`/pocs/${pocId.value}`)
  } else {
    router.push('/pocs')
  }
}

function addAffected() {
  form.affected_versions.push({
    version_start: '',
    version_start_type: '>=',
    version_end: '',
    version_end_type: '<=',
  })
}

function removeAffected(idx: number) {
  form.affected_versions.splice(idx, 1)
}

function addRef() {
  form.references.push({ url: '', label: '' })
}

function removeRef(idx: number) {
  form.references.splice(idx, 1)
}

async function verifyRef(idx: number) {
  const ref = form.references[idx]
  if (!ref.url.trim()) return
  ref._verifying = true
  ref._verified = false
  try {
    const res = await verifyUrl(ref.url.trim())
    ref._verified = res.reachable
    if (!res.reachable) {
      ElMessage.warning(`链接不可达: ${res.error || `HTTP ${res.status_code}`}`)
    } else {
      ElMessage.success(`链接可达 (HTTP ${res.status_code})`)
    }
  } catch {
    ref._verified = false
  } finally {
    ref._verifying = false
  }
}

onMounted(() => {
  loadTags()
  loadData().then(() => {
    // 新建 POC 时默认添加一条空版本范围
    if (!isEdit.value && form.affected_versions.length === 0) {
      addAffected()
    }
  })
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.poc-form-view {
  height: 100%;
}

.form-grid {
  display: grid;
  grid-template-columns: 520px 1fr;
  gap: $spacing-xxl;
  height: calc(100vh - 180px);
}

.form-left {
  overflow-y: auto;
  padding-right: $spacing-sm;
}

.form-right {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.form-section {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-xl;
  margin-bottom: $spacing-xl;
}

.editor-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  margin-bottom: 0;
}

.section-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-xl;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-xl;

  .section-title {
    margin-bottom: 0;
  }
}

.editor-tools {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.mode-switch {
  :deep(.el-radio-button__inner) {
    padding: 6px 14px;
  }
}

.builder-container {
  display: flex;
  flex-direction: column;
}

.builder-actions {
  display: flex;
  gap: $spacing-sm;
  padding-top: $spacing-sm;
  border-top: 1px solid $border-color;
  margin-top: $spacing-sm;
}

.source-hint,
.format-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: $spacing-sm;
  padding: 6px 10px;
  font-size: $font-caption;
  color: $text-disabled;
  background: rgba($info, 0.05);
  border-radius: $radius-sm;
}

.editor-container {
  flex: 1;
  min-height: 0;
}

.code-textarea {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: $bg-tertiary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  color: $text-primary;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
  padding: $spacing-lg;
  resize: none;
  outline: none;
  transition: border-color $transition-fast;

  &:focus {
    border-color: $accent;
  }

  &::placeholder {
    color: $text-disabled;
  }
}

// ── 受影响版本 ────────────────────────────────────────────────
.affected-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;
}

.affected-row {
  display: flex;
  align-items: flex-start;
  gap: $spacing-sm;
  padding: $spacing-md;
  background: $bg-tertiary;
  border: 1px solid $border-subtle;
  border-radius: $radius-sm;
}

.affected-fields {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: $spacing-sm;
  min-width: 0;
}

.affected-group {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.affected-label {
  font-size: $font-caption;
  color: $text-disabled;
  white-space: nowrap;
  width: 28px;
  flex-shrink: 0;
}

.op-select {
  width: 80px;
  flex-shrink: 0;
}

.ver-input {
  flex: 1;
  min-width: 0;
}

.affected-remove {
  flex-shrink: 0;
  margin-top: 2px;
}

// ── 参考链接 ──────────────────────────────────────────────────
.reference-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.reference-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: $spacing-sm $spacing-md;
  background: $bg-tertiary;
  border: 1px solid $border-subtle;
  border-radius: $radius-sm;
}

.ref-fields {
  display: flex;
  flex: 1;
  gap: 8px;
  min-width: 0;
}

.ref-url {
  flex: 2;
  min-width: 0;
}

.ref-label {
  flex: 1;
  min-width: 0;
}

.ref-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.ref-verified {
  color: $active !important;
}
</style>