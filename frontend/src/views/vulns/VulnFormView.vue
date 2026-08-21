<template>
  <div v-loading="loading" class="vuln-form-view">
    <PageHeader :title="isEdit ? $t('nav.vulnEdit') : $t('nav.vulnCreate')" :description="headerDesc">
      <template #actions>
        <el-button :icon="Back" @click="cancel">{{ $t('common.action.cancel') }}</el-button>
        <el-button v-if="!isEdit" :icon="Refresh" :loading="savingContinue" @click="handleSaveAndContinue">
          {{ $t('vulnForm.saveContinue') }}
        </el-button>
        <el-button type="primary" :icon="Edit" :loading="saving" @click="handleSave">
          {{ isEdit ? $t('common.action.save') : $t('common.action.create') }}
        </el-button>
      </template>
    </PageHeader>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="right"
      class="edit-form"
    >
      <!-- 基本信息 -->
      <section class="detail-section">
        <h3 class="section-title"><i class="title-bar" />{{ $t('vulnForm.sections.basic') }}</h3>
        <el-form-item :label="$t('vulnForm.fields.cveId')" prop="cve_id">
          <el-input
            v-model="form.cve_id"
            :disabled="isEdit"
            placeholder="CVE-YYYY-NNNNN"
            class="mono"
          />
          <span class="field-hint">
            {{ isEdit ? $t('vulnForm.cveIdHintEdit') : $t('vulnForm.cveIdHintNew') }}
          </span>
        </el-form-item>
        <el-form-item :label="$t('vulnForm.fields.title')" prop="title">
          <el-input v-model="form.title" :placeholder="$t('vulnForm.placeholders.title')" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item :label="$t('vulnForm.fields.vendor')" prop="vendor">
          <el-input v-model="form.vendor" placeholder="apache" maxlength="128" />
        </el-form-item>
        <el-form-item :label="$t('vulnForm.fields.severity')" prop="severity">
          <el-select v-model="form.severity" :placeholder="$t('vulnForm.placeholders.severity')" clearable class="full">
            <el-option v-for="s in SEVERITY_OPTIONS" :key="s.value" :label="$t(s.label)" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('vulnForm.fields.cvss')" prop="cvss">
          <el-input-number
            v-model="form.cvss"
            :min="0"
            :max="10"
            :step="0.1"
            :precision="1"
            controls-position="right"
            placeholder="0–10"
          />
        </el-form-item>
        <el-form-item :label="$t('vulnForm.fields.cvssMetrics')" prop="cvss_metrics">
          <el-input v-model="form.cvss_metrics" placeholder="CVSS:3.1/AV:N/AC:L/..." maxlength="255" class="mono" />
        </el-form-item>
      </section>

      <!-- 漏洞描述 -->
      <section class="detail-section">
        <h3 class="section-title"><i class="title-bar" />{{ $t('vulnForm.sections.description') }}</h3>
        <el-form-item :label="$t('vulnForm.fields.description')" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="5"
            :placeholder="$t('vulnForm.placeholders.markdown')"
          />
        </el-form-item>
      </section>

      <!-- 受影响产品 -->
      <section class="detail-section">
        <div class="section-head-row">
          <h3 class="section-title"><i class="title-bar" />{{ $t('vulnForm.sections.products') }}</h3>
          <el-button size="small" :icon="Plus" @click="addProduct">{{ $t('vulnForm.addProduct') }}</el-button>
        </div>
        <p v-if="!form.product.length" class="no-data">{{ $t('vulnForm.noProducts') }}</p>
        <div v-for="(p, idx) in form.product" :key="p._key" class="sub-card">
          <div class="sub-card-head">
            <span class="sub-card-title">{{ $t('vulnForm.productN', { n: idx + 1 }) }}</span>
            <el-button text size="small" type="danger" :icon="Delete" @click="removeProduct(idx)">{{ $t('vulnForm.remove') }}</el-button>
          </div>
          <div class="sub-grid">
            <el-form-item :label="$t('vulnForm.fields.vendor')"><el-input v-model="p.vendor" :placeholder="$t('vulnForm.fields.vendor')" /></el-form-item>
            <el-form-item :label="$t('vulnForm.fields.product')"><el-input v-model="p.product" :placeholder="$t('vulnForm.placeholders.productName')" /></el-form-item>
            <el-form-item :label="$t('vulnForm.fields.exactVersion')"><el-input v-model="p.version" placeholder="2.14.1" /></el-form-item>
            <el-form-item :label="$t('vulnForm.fields.startVersion')"><el-input v-model="p.version_start" placeholder="2.0" /></el-form-item>
            <el-form-item :label="$t('vulnForm.fields.startType')">
              <el-select v-model="p.version_start_type" class="full">
                <el-option :label="$t('vulnForm.including')" value="including" />
                <el-option :label="$t('vulnForm.excluding')" value="excluding" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('vulnForm.fields.endVersion')"><el-input v-model="p.version_end" placeholder="2.14.1" /></el-form-item>
            <el-form-item :label="$t('vulnForm.fields.endType')">
              <el-select v-model="p.version_end_type" class="full">
                <el-option :label="$t('vulnForm.including')" value="including" />
                <el-option :label="$t('vulnForm.excluding')" value="excluding" />
              </el-select>
            </el-form-item>
          </div>
        </div>
      </section>

      <!-- 修复建议 -->
      <section class="detail-section">
        <h3 class="section-title"><i class="title-bar" />{{ $t('vulnForm.sections.remediation') }}</h3>
        <el-form-item :label="$t('vulnForm.fields.patch')">
          <el-input
            v-model="form.remediation.mitigation"
            type="textarea"
            :rows="3"
            :placeholder="$t('vulnForm.placeholders.patch')"
          />
        </el-form-item>
        <el-form-item :label="$t('vulnForm.fields.workaround')">
          <el-input
            v-model="form.remediation.workaround"
            type="textarea"
            :rows="3"
            :placeholder="$t('vulnForm.placeholders.workaround')"
          />
        </el-form-item>
      </section>

      <!-- 参考链接 -->
      <section class="detail-section">
        <div class="section-head-row">
          <h3 class="section-title"><i class="title-bar" />{{ $t('vulnForm.sections.references') }}</h3>
          <el-button size="small" :icon="Plus" @click="addReference">{{ $t('vulnForm.addLink') }}</el-button>
        </div>
        <p v-if="!form.reference.length" class="no-data">{{ $t('vulnForm.noReferences') }}</p>
        <div v-for="(r, idx) in form.reference" :key="r._key" class="ref-row">
          <span class="ref-index">{{ idx + 1 }}</span>
          <el-input v-model="r.url" placeholder="https://..." class="ref-url" />
          <el-input v-model="r.label" :placeholder="$t('vulnForm.placeholders.refLabel')" class="ref-label" />
          <el-button text type="danger" :icon="Delete" @click="removeReference(idx)" />
        </div>
      </section>
    </el-form>

    <div class="form-footer">
      <el-button :icon="Back" @click="cancel">{{ $t('common.action.cancel') }}</el-button>
      <el-button v-if="!isEdit" :icon="Refresh" :loading="savingContinue" @click="handleSaveAndContinue">
        {{ $t('vulnForm.saveContinue') }}
      </el-button>
      <el-button type="primary" :icon="Edit" :loading="saving" @click="handleSave">
        {{ isEdit ? $t('common.action.save') : $t('common.action.create') }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Back, Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import { createVuln, getVuln, updateVuln } from '@/api/vuln'
import { SEVERITY_OPTIONS } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import type { VulnUpdatePayload } from '@/types/vuln'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const isEdit = computed(() => !!route.params.id)
const vulnId = computed(() => Number(route.params.id))
const headerDesc = computed(() =>
  isEdit.value ? form.cve_id : t('vulnForm.headerDescNew')
)

const loading = ref(isEdit.value)
const saving = ref(false)
const savingContinue = ref(false)
const formRef = ref<FormInstance>()

interface ProductRow {
  _key: number
  vendor: string
  product: string
  version: string
  version_start: string
  version_start_type: string
  version_end: string
  version_end_type: string
}
interface ReferenceRow {
  _key: number
  url: string
  label: string
}

const form = reactive({
  cve_id: '',
  vendor: '',
  title: '',
  description: '',
  cvss: undefined as number | undefined,
  severity: '',
  cvss_metrics: '',
  product: [] as ProductRow[],
  remediation: { mitigation: '', workaround: '' },
  reference: [] as ReferenceRow[],
})

const rules = computed<FormRules>(() => ({
  cve_id: isEdit.value
    ? []
    : [
        { required: true, message: t('vulnForm.rules.cveIdRequired'), trigger: 'blur' },
        { pattern: /^CVE-\d{4}-\d{4,}$/, message: t('vulnForm.rules.cveIdPattern'), trigger: 'blur' },
      ],
  cvss: [{ type: 'number', min: 0, max: 10, message: t('vulnForm.rules.cvssRange'), trigger: 'blur' }],
}))

// 行稳定 key 生成（用于 v-for，避免增删时输入错位）
let _keySeq = 1
const genKey = () => _keySeq++

/** 构造一条空的受影响产品行。 */
function emptyProduct(): ProductRow {
  return {
    _key: genKey(),
    vendor: '',
    product: '',
    version: '',
    version_start: '',
    version_start_type: 'including',
    version_end: '',
    version_end_type: 'including',
  }
}

/** 加载 CVE 详情并填充表单（仅编辑模式）。 */
async function loadData() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const vuln = await getVuln(vulnId.value)
    form.cve_id = vuln.cve_id
    form.vendor = vuln.vendor || ''
    form.title = vuln.title || ''
    form.description = vuln.description || ''
    form.cvss = vuln.cvss ?? undefined
    form.severity = vuln.severity || ''
    form.cvss_metrics = vuln.cvss_metrics || ''
    form.product = (vuln.product || []).map((p) => ({
      _key: genKey(),
      vendor: p.vendor || '',
      product: p.product || '',
      version: p.version || '',
      version_start: p.version_start || '',
      version_start_type: p.version_start_type || 'including',
      version_end: p.version_end || '',
      version_end_type: p.version_end_type || 'including',
    }))
    form.remediation = {
      mitigation: vuln.remediation?.mitigation || '',
      workaround: vuln.remediation?.workaround || '',
    }
    form.reference = (vuln.reference || []).map((r) => ({
      _key: genKey(),
      url: r.url,
      label: r.label || '',
    }))
  } catch {
    router.push('/vulns')
  } finally {
    loading.value = false
  }
}

/** 新增一条受影响产品。 */
function addProduct() {
  form.product.push(emptyProduct())
}

/** 移除指定受影响产品。 */
function removeProduct(idx: number) {
  form.product.splice(idx, 1)
}

/** 新增一条参考链接。 */
function addReference() {
  form.reference.push({ _key: genKey(), url: '', label: '' })
}

/** 移除指定参考链接。 */
function removeReference(idx: number) {
  form.reference.splice(idx, 1)
}

/** 取消返回（编辑回详情，新建回列表）。 */
function cancel() {
  router.push(isEdit.value ? `/vulns/${vulnId.value}` : '/vulns')
}

/** 构造可编辑字段载荷（不含 cve_id）。 */
function buildEditablePayload(): VulnUpdatePayload {
  return {
    vendor: form.vendor.trim() || null,
    title: form.title.trim() || null,
    description: form.description.trim() || null,
    cvss: form.cvss ?? null,
    severity: form.severity || null,
    cvss_metrics: form.cvss_metrics.trim() || null,
    product: form.product.length
      ? form.product.map((p) => ({
          vendor: p.vendor.trim() || null,
          product: p.product.trim() || null,
          version: p.version.trim() || null,
          version_start: p.version_start.trim() || null,
          version_start_type: p.version_start_type,
          version_end: p.version_end.trim() || null,
          version_end_type: p.version_end_type,
        }))
      : null,
    remediation:
      form.remediation.mitigation.trim() || form.remediation.workaround.trim()
        ? {
            mitigation: form.remediation.mitigation.trim() || null,
            workaround: form.remediation.workaround.trim() || null,
          }
        : null,
    reference: form.reference
      .filter((r) => r.url.trim())
      .map((r) => ({ url: r.url.trim(), label: r.label.trim() || null })),
  }
}

/** 重置表单为空白（保存并继续后复用）。 */
function resetForm() {
  form.cve_id = ''
  form.vendor = ''
  form.title = ''
  form.description = ''
  form.cvss = undefined
  form.severity = ''
  form.cvss_metrics = ''
  form.product = []
  form.remediation = { mitigation: '', workaround: '' }
  form.reference = []
  formRef.value?.clearValidate()
}

/** 保存：编辑→更新，新建→创建，成功后跳详情。 */
async function handleSave() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return // 校验未通过
  }
  saving.value = true
  try {
    const payload = buildEditablePayload()
    if (isEdit.value) {
      await updateVuln(vulnId.value, payload)
      ElMessage.success(t('vulnForm.messages.saveSuccess'))
      router.push(`/vulns/${vulnId.value}`)
    } else {
      const created = await createVuln({ cve_id: form.cve_id.trim(), ...payload })
      ElMessage.success(t('vulnForm.messages.createSuccess'))
      router.push(`/vulns/${created.id}`)
    }
  } finally {
    saving.value = false
  }
}

/** 保存并继续：创建后清空表单，留在本页继续录入。 */
async function handleSaveAndContinue() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  savingContinue.value = true
  try {
    const created = await createVuln({ cve_id: form.cve_id.trim(), ...buildEditablePayload() })
    ElMessage.success(t('vulnForm.messages.createdContinue', { cve: created.cve_id }))
    resetForm()
  } finally {
    savingContinue.value = false
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.vuln-form-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.edit-form {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  padding-bottom: $spacing-md;
}

.detail-section {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-lg $spacing-xl;
}

.section-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-md;

  .section-title {
    margin-bottom: 0;
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-md;
}

.title-bar {
  display: inline-block;
  width: 3px;
  height: 1em;
  border-radius: 2px;
  background: var(--vs-accent);
}

.field-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: $text-disabled;
}

.full {
  width: 100%;
}

.mono {
  :deep(input) {
    font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  }
}

/* ── 受影响产品子卡片 ── */
.sub-card {
  background: $bg-tertiary;
  border: 1px solid $border-subtle;
  border-radius: $radius-sm;
  padding: $spacing-md $spacing-lg;
  margin-bottom: $spacing-sm;

  &:last-child {
    margin-bottom: 0;
  }
}

.sub-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-md;
}

.sub-card-title {
  font-size: $font-caption;
  font-weight: 600;
  color: $text-secondary;
}

.sub-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 $spacing-xl;

  :deep(.el-form-item) {
    margin-bottom: $spacing-sm;
  }
}

/* ── 参考链接行 ── */
.ref-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;

  &:last-child {
    margin-bottom: 0;
  }
}

.ref-index {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  font-size: $font-caption;
  color: $text-disabled;
}

.ref-url {
  flex: 2;
}

.ref-label {
  flex: 1;
}

.no-data {
  color: $text-disabled;
  font-size: $font-body;
  margin: 0;
  padding: $spacing-sm 0;
}

/* ── 底部操作栏：贴底封闭 ── */
.form-footer {
  position: sticky;
  bottom: 0;
  z-index: 10;
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: $spacing-sm;
  padding: $spacing-md $spacing-xl;
  background: $bg-secondary;
  border-top: 1px solid $border-color;
  border-radius: 0;
}
</style>
