<template>
  <div class="user-manage-view">
    <PageHeader title="用户管理">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建用户</el-button>
      </template>
    </PageHeader>

    <el-table :data="items" v-loading="loading" stripe class="user-table" height="calc(100vh - 280px)">
      <el-table-column prop="id" label="ID" width="64" />
      <el-table-column prop="username" label="用户名" width="140">
        <template #default="{ row }">
          <span class="user-name">{{ row.username }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="200">
        <template #default="{ row }">
          <span class="cell-text">{{ row.email || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="角色" width="100" align="center">
        <template #default="{ row }">
          <span class="role-badge" :class="row.role">{{ roleLabel(row.role) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="92" align="center">
        <template #default="{ row }">
          <StatusBadge :status="row.is_active ? 'active' : 'disabled'" />
        </template>
      </el-table-column>
      <el-table-column label="最后登录" width="160">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.last_login_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">
          <span class="cell-time">{{ formatDate(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button
            v-if="row.username !== 'admin'"
            text size="small"
            type="danger"
            @click="handleDelete(row)"
          >
            删除
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
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑用户' : '新建用户'" width="420">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEditing" placeholder="3-64 字符，字母数字下划线" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="可选" />
        </el-form-item>
        <el-form-item label="密码" :prop="isEditing ? undefined : 'password'">
          <el-input v-model="form.password" type="password" show-password :placeholder="isEditing ? '留空则不修改' : '至少 8 位'" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" class="w-full">
            <el-option label="查看者" value="viewer" />
            <el-option label="编辑者" value="editor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEditing" label="启用" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listUsers, createUser, updateUser, deleteUser } from '@/api/user'
import { formatDate } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

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
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_.-]{3,64}$/, message: '3-64 字符，仅允许字母数字下划线连字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
}

function roleLabel(role: string): string {
  const map: Record<string, string> = { viewer: '查看者', editor: '编辑者', admin: '管理员' }
  return map[role] || role
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
      ElMessage.success('用户更新成功')
    } else {
      await createUser({
        username: form.username,
        email: form.email || undefined,
        password: form.password,
        role: form.role,
      })
      ElMessage.success('用户创建成功')
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
    ElMessage.success('用户已删除')
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