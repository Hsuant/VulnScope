<template>
  <div class="subscription-view">
    <PageHeader :title="$t('subscription.title')">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
          {{ $t('subscription.create') }}
        </el-button>
      </template>
    </PageHeader>

    <!-- 列表 -->
    <el-table
      :data="items"
      v-loading="loading"
      stripe
      class="sub-table"
      height="calc(100vh - 240px)"
    >
      <el-table-column :label="$t('subscription.fields.type')" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="tagType(row.sub_type)" size="small">
            {{ $t(`subscription.form.type${capitalize(row.sub_type)}`) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('subscription.fields.target')" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="target-text">{{ row.target_display || row.target_id }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('subscription.fields.notify')" width="200" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.notify_on_update"
            :active-text="$t('subscription.form.notifyOnUpdate')"
            inline-prompt
            size="small"
            @change="(val: boolean) => handleToggleNotify(row, 'notify_on_update', val)"
          />
          <el-switch
            :model-value="row.notify_on_new"
            :active-text="$t('subscription.form.notifyOnNew')"
            inline-prompt
            size="small"
            style="margin-left: 8px"
            @change="(val: boolean) => handleToggleNotify(row, 'notify_on_new', val)"
          />
        </template>
      </el-table-column>
      <el-table-column :label="$t('subscription.fields.createdAt')" width="160" align="center">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('common.columns.actions')" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" type="danger" @click="handleDelete(row)">
            {{ $t('common.action.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <EmptyState v-if="!loading && !total" :title="$t('subscription.empty')" />

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

    <!-- 新建订阅对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="$t('subscription.create')"
      width="560px"
      align-center
      destroy-on-close
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-position="top" class="subscription-form">
        <!-- 订阅类型：分段选择 -->
        <div class="form-section">
          <span class="section-label">{{ $t('subscription.form.type') }}</span>
          <el-radio-group v-model="form.sub_type" class="type-selector" @change="onTypeChange">
            <el-radio-button v-for="opt in typeOptions" :key="opt.value" :value="opt.value">
              <el-icon><component :is="opt.icon" /></el-icon>
              <span>{{ $t(opt.label) }}</span>
            </el-radio-button>
          </el-radio-group>
          <p class="type-hint">{{ typeHint }}</p>
        </div>

        <!-- 订阅目标 -->
        <div class="form-section">
          <span class="section-label">{{ $t('subscription.form.target') }}</span>
          <el-form-item prop="target_id" class="target-item">
            <el-input
              v-if="form.sub_type === 'cve'"
              ref="targetInputRef"
              v-model="form.target_id"
              :placeholder="$t('subscription.form.targetPlaceholderCve')"
              clearable
              @keyup.enter="handleCreate"
            />
            <el-select
              v-else-if="form.sub_type === 'vendor'"
              ref="targetSelectRef"
              v-model="form.target_id"
              :placeholder="$t('subscription.form.targetPlaceholderVendor')"
              filterable
              :loading="vendorsLoading"
              style="width: 100%"
            >
              <el-option
                v-for="v in vendorOptions"
                :key="v.slug"
                :label="v.name"
                :value="v.slug"
              />
            </el-select>
            <el-select
              v-else
              ref="targetSelectRef"
              v-model="form.target_id"
              :placeholder="$t('subscription.form.targetPlaceholderTag')"
              filterable
              clearable
              :loading="tagsLoading"
              style="width: 100%"
            >
              <el-option
                v-for="tag in tagOptions"
                :key="tag.id"
                :label="`${tag.namespace}:${tag.name}`"
                :value="String(tag.id)"
              >
                <span class="tag-dot" :style="{ background: tag.color || 'var(--vs-accent)' }" />
                <span>{{ tag.namespace }}:</span>
                <span>{{ tag.name }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </div>

        <!-- 通知偏好：卡片式 -->
        <div class="form-section">
          <span class="section-label">{{ $t('subscription.form.notifyPref') }}</span>
          <div class="notify-cards">
            <div class="notify-card">
              <div class="notify-info">
                <div class="notify-title">{{ $t('subscription.form.notifyOnUpdate') }}</div>
                <div class="notify-desc">{{ $t('subscription.form.notifyOnUpdateDesc') }}</div>
              </div>
              <el-switch v-model="form.notify_on_update" />
            </div>
            <div class="notify-card">
              <div class="notify-info">
                <div class="notify-title">{{ $t('subscription.form.notifyOnNew') }}</div>
                <div class="notify-desc">{{ $t('subscription.form.notifyOnNewDesc') }}</div>
              </div>
              <el-switch v-model="form.notify_on_new" />
            </div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.action.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">
          {{ $t('common.action.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model:visible="deleteDialogVisible"
      :title="$t('common.title.deleteConfirm')"
      :message="$t('subscription.deleteConfirm')"
      type="danger"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Plus, Aim, OfficeBuilding, PriceTag } from '@element-plus/icons-vue'
import {
  listSubscriptions,
  createSubscription,
  updateSubscription,
  deleteSubscription,
  type SubscriptionItem,
  type SubscriptionCreatePayload,
} from '@/api/subscription'
import { listVendors } from '@/api/product'
import { listTags } from '@/api/tag'
import { formatDate } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const { t } = useI18n()

const items = ref<SubscriptionItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showCreateDialog = ref(false)
const submitting = ref(false)
const deleteTarget = ref<SubscriptionItem | null>(null)
const deleteDialogVisible = ref(false)
const formRef = ref()
const targetInputRef = ref()
const targetSelectRef = ref()
const vendorOptions = ref<{ slug: string; name: string }[]>([])
const tagOptions = ref<{ id: number; namespace: string; name: string; color: string | null }[]>([])
const vendorsLoading = ref(false)
const tagsLoading = ref(false)

const form = ref<SubscriptionCreatePayload>({
  sub_type: 'cve',
  target_id: '',
  notify_on_update: true,
  notify_on_new: true,
})

/** 类型选项（图标 + 文案 key） */
const typeOptions = [
  { value: 'cve', label: 'subscription.form.typeCve', icon: Aim },
  { value: 'vendor', label: 'subscription.form.typeVendor', icon: OfficeBuilding },
  { value: 'tag', label: 'subscription.form.typeTag', icon: PriceTag },
]

/** 当前类型对应的提示文案 */
const typeHint = computed(() => t(`subscription.form.hint${capitalize(form.value.sub_type)}`))

/** CVE 编号格式校验 */
function validateCveId(_rule: unknown, value: string, callback: (err?: Error) => void) {
  if (!value) return callback(new Error(t('subscription.form.target')))
  const pattern = /^CVE-\d{4}-\d{4,}$/i
  callback(pattern.test(value.trim()) ? undefined : new Error(t('subscription.form.validation.cveFormat')))
}

const rules = {
  sub_type: [{ required: true, message: t('subscription.form.type'), trigger: 'change' }],
  target_id: [{ required: true, message: t('subscription.form.target'), trigger: 'blur' }],
}
/** CVE 类型额外启用格式校验（动态合并） */
const cveRules = { target_id: validateCveId }
const formRules = computed(() =>
  form.value.sub_type === 'cve'
    ? { ...rules, ...cveRules }
    : rules,
)

onMounted(() => {
  loadData()
  loadVendors()
  loadTags()
})

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function tagType(subType: string) {
  const map: Record<string, string> = { cve: 'danger', vendor: 'warning', tag: 'info' }
  return map[subType] || ''
}

async function loadData() {
  loading.value = true
  try {
    const res = await listSubscriptions({ page: page.value, page_size: pageSize.value })
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function loadVendors() {
  vendorsLoading.value = true
  try {
    const res = await listVendors()
    vendorOptions.value = res.items
  } catch {
    // 静默处理
  } finally {
    vendorsLoading.value = false
  }
}

async function loadTags() {
  tagsLoading.value = true
  try {
    const res = await listTags()
    tagOptions.value = res.items
  } catch {
    // 静默处理
  } finally {
    tagsLoading.value = false
  }
}

/** 切换类型：清空目标值并聚焦输入框 */
function onTypeChange() {
  form.value.target_id = ''
  formRef.value?.clearValidate('target_id')
  nextTick(() => {
    if (form.value.sub_type === 'cve') {
      targetInputRef.value?.focus()
    } else {
      targetSelectRef.value?.focus()
    }
  })
}

/** 对话框关闭后重置表单 */
function resetForm() {
  form.value = { sub_type: 'cve', target_id: '', notify_on_update: true, notify_on_new: true }
  formRef.value?.clearValidate()
}

async function handleCreate() {
  if (form.value.sub_type === 'cve' && form.value.target_id) {
    form.value.target_id = form.value.target_id.trim().toUpperCase()
  }
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createSubscription(form.value)
    ElMessage.success(t('subscription.createSuccess'))
    showCreateDialog.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function handleToggleNotify(row: SubscriptionItem, field: 'notify_on_update' | 'notify_on_new', val: boolean) {
  try {
    await updateSubscription(row.id, { [field]: val })
    row[field] = val
    ElMessage.success(t('subscription.updateSuccess'))
  } catch {
    // 恢复原值
  }
}

function handleDelete(row: SubscriptionItem) {
  deleteTarget.value = row
  deleteDialogVisible.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteSubscription(deleteTarget.value.id)
    ElMessage.success(t('subscription.deleteSuccess'))
    deleteDialogVisible.value = false
    deleteTarget.value = null
    loadData()
  } catch {
    // 静默处理
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.subscription-view {
  padding: 0;
}

.sub-table {
  :deep(.target-text) {
    font-weight: 500;
    color: $text-primary;
  }

  :deep(.cell-time) {
    color: $text-secondary;
    font-size: $font-caption;
  }
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: $spacing-lg 0;
}

// ── 新建订阅对话框 ──────────────────────────────────────────
.subscription-form {
  // 区块分隔
  .form-section {
    margin-bottom: $spacing-lg;

    & + .form-section {
      padding-top: $spacing-lg;
      border-top: 1px solid $border-subtle;
    }
  }

  .section-label {
    display: block;
    font-size: $font-caption;
    font-weight: 600;
    color: $text-secondary;
    margin-bottom: $spacing-sm;
  }

  // 类型分段按钮
  .type-selector {
    display: flex;
    gap: $spacing-sm;
    width: 100%;

    :deep(.el-radio-button) {
      flex: 1;

      .el-radio-button__inner {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        width: 100%;
        padding: 10px 12px;
        border-radius: $radius-md;
        font-size: $font-body;
      }

      &:first-child .el-radio-button__inner {
        border-left: 1px solid $border-color;
      }
    }
  }

  // 类型提示
  .type-hint {
    margin: $spacing-sm 0 0;
    font-size: $font-caption;
    line-height: 1.5;
    color: $text-disabled;
  }

  // 目标输入项（去除多余间距）
  .target-item {
    margin-bottom: 0;

    :deep(.el-form-item__content) {
      line-height: normal;
    }
  }

  // 标签选项中的颜色圆点
  .tag-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
  }

  // 通知偏好卡片
  .notify-cards {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  .notify-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $spacing-lg;
    padding: $spacing-sm $spacing-md;
    border: 1px solid $border-color;
    border-radius: $radius-md;
    background: $bg-primary;

    .notify-info {
      flex: 1;
      min-width: 0;
    }

    .notify-title {
      font-size: $font-body;
      font-weight: 500;
      color: $text-primary;
    }

    .notify-desc {
      margin-top: 2px;
      font-size: $font-caption;
      color: $text-secondary;
    }
  }
}
</style>