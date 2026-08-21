<template>
  <div class="user-manage-view">
    <PageHeader :title="$t('nav.userManage')">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">{{ $t('userManage.createUser') }}</el-button>
      </template>
    </PageHeader>

    <el-table :data="items" v-loading="loading" stripe class="user-table" height="calc(100vh - 280px)">
      <el-table-column prop="id" label="ID" width="64" />
      <el-table-column prop="username" :label="$t('userManage.columns.username')" width="140">
        <template #default="{ row }">
          <span class="user-name">{{ row.username }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="email" :label="$t('userManage.columns.email')" min-width="200">
        <template #default="{ row }">
          <span class="cell-text">{{ row.email || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('userManage.columns.role')" width="100" align="center">
        <template #default="{ row }">
          <span class="role-badge" :class="row.role">{{ roleLabel(row.role) }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('common.columns.status')" width="92" align="center">
        <template #default="{ row }">
          <StatusBadge :status="row.is_active ? 'active' : 'disabled'" />
        </template>
      </el-table-column>
      <el-table-column :label="$t('userManage.columns.lastLogin')" width="160">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.last_login_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('userManage.columns.createdAt')" width="160">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('common.columns.actions')" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openEditDialog(row)">{{ $t('common.action.edit') }}</el-button>
          <el-button
            v-if="row.username !== 'admin'"
            text size="small"
            type="danger"
            @click="handleDelete(row)"
          >
            {{ $t('common.action.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadData"
        @size-change="loadData"
      />
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? $t('userManage.editUser') : $t('userManage.createUser')" width="420">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item :label="$t('userManage.fields.username')" prop="username">
          <el-input v-model="form.username" :disabled="isEditing" :placeholder="$t('userManage.placeholders.username')" />
        </el-form-item>
        <el-form-item :label="$t('userManage.fields.email')" prop="email">
          <el-input v-model="form.email" :placeholder="$t('userManage.placeholders.emailOptional')" />
        </el-form-item>
        <el-form-item :label="$t('userManage.fields.password')" :prop="isEditing ? undefined : 'password'">
          <el-input v-model="form.password" type="password" show-password :placeholder="isEditing ? $t('userManage.placeholders.passwordEdit') : $t('userManage.placeholders.passwordNew')" />
        </el-form-item>
        <el-form-item :label="$t('userManage.fields.role')" prop="role">
          <el-select v-model="form.role" class="w-full">
            <el-option :label="$t('enums.role.viewer')" value="viewer" />
            <el-option :label="$t('enums.role.editor')" value="editor" />
            <el-option :label="$t('enums.role.admin')" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEditing" :label="$t('userManage.fields.active')" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.action.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">{{ $t('common.action.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listUsers, createUser, updateUser, deleteUser } from '@/api/user'
import { formatDate } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const { t } = useI18n()

interface UserRow {
  id: number
  username: string
  email: string | null
  role: string
  is_active: boolean
  last_login_at: string | null
  created_at: string | null
}

const loading = ref(true)
const items = ref<UserRow[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  username: '',
  email: '',
  password: '',
  role: 'viewer',
  is_active: true,
})

const rules: Record<string, any> = {
  username: [
    { required: true, message: t('userManage.rules.usernameRequired'), trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_.-]{3,64}$/, message: t('userManage.rules.usernamePattern'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: t('userManage.rules.passwordRequired'), trigger: 'blur' },
    { min: 8, message: t('userManage.rules.passwordMin'), trigger: 'blur' },
  ],
}

function roleLabel(role: string): string {
  return t('enums.role.' + role)
}

async function loadData() {
  loading.value = true
  try {
    const res = await listUsers({ page: page.value, page_size: pageSize.value })
    items.value = res.items
    total.value = res.total
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEditing.value = false
  editingId.value = null
  form.username = ''
  form.email = ''
  form.password = ''
  form.role = 'viewer'
  form.is_active = true
  dialogVisible.value = true
}

function openEditDialog(row: UserRow) {
  isEditing.value = true
  editingId.value = row.id
  form.username = row.username
  form.email = row.email || ''
  form.password = ''
  form.role = row.role
  form.is_active = row.is_active
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      await updateUser(editingId.value, {
        email: form.email || undefined,
        password: form.password || undefined,
        role: form.role,
        is_active: form.is_active,
      })
      ElMessage.success(t('userManage.messages.updateSuccess'))
    } else {
      await createUser({
        username: form.username,
        email: form.email || undefined,
        password: form.password,
        role: form.role,
      })
      ElMessage.success(t('userManage.messages.createSuccess'))
    }
    dialogVisible.value = false
    loadData()
  } catch {
    // handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: UserRow) {
  try {
    await deleteUser(row.id)
    ElMessage.success(t('userManage.messages.deleteSuccess'))
    loadData()
  } catch {
    // handled by interceptor
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.user-name {
  font-weight: 500;
}

.role-badge {
  display: inline-block;
  padding: 1px 8px;
  font-size: $font-caption;
  border-radius: $radius-sm;
  font-weight: 500;
  white-space: nowrap;

  &.admin {
    color: $archived;
    background: rgba($archived, 0.1);
    border: 1px solid rgba($archived, 0.25);
  }
  &.editor {
    color: $accent;
    background: rgba($accent, 0.1);
    border: 1px solid rgba($accent, 0.25);
  }
  &.viewer {
    color: $text-secondary;
    background: rgba($info, 0.1);
    border: 1px solid rgba($info, 0.25);
  }
}

.cell-text {
  color: $text-secondary;
  font-size: $font-caption;
}

.cell-time {
  color: $text-disabled;
  font-size: $font-caption;
}

.pagination-wrap {
  padding-top: $spacing-lg;
}
</style>