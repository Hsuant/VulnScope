<template>
  <div class="profile-view">
    <div class="profile-container">
      <PageHeader title="个人信息" description="查看和修改个人账号信息" />

      <!-- ── 用户头像与概要 ── -->
      <div class="profile-card avatar-card">
        <div class="avatar-decoration">
          <div class="avatar-ring">
            <div class="avatar-inner">
              <span class="avatar-text">{{ userInitial }}</span>
            </div>
          </div>
          <div class="avatar-glow" />
        </div>
        <div class="avatar-info">
          <h2 class="avatar-name">{{ user?.username }}</h2>
          <div class="avatar-meta">
            <span class="role-tag" :class="'role--' + user?.role">
              <el-icon :size="14"><UserFilled /></el-icon>
              {{ roleLabel }}
            </span>
            <span v-if="user?.is_active" class="status-tag status--active">
              <el-icon :size="12"><CircleCheck /></el-icon>
              正常
            </span>
            <span v-else class="status-tag status--disabled">
              <el-icon :size="12"><RemoveFilled /></el-icon>
              已停用
            </span>
          </div>
        </div>
      </div>

      <!-- ── 基本信息编辑 ── -->
      <div class="profile-card form-card">
        <div class="section-header">
          <el-icon :size="20"><EditPen /></el-icon>
          <span>编辑资料</span>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          class="profile-form"
        >
          <!-- 用户名（只读） -->
          <div class="form-row">
            <div class="form-label">
              <el-icon :size="16"><UserFilled /></el-icon>
              <span>用户名</span>
            </div>
            <div class="form-control">
              <el-input :model-value="user?.username" disabled>
                <template #prefix>
                  <el-icon><UserFilled /></el-icon>
                </template>
              </el-input>
              <p class="form-tip">用户名不可修改</p>
            </div>
          </div>

          <!-- 邮箱 -->
          <div class="form-row">
            <div class="form-label">
              <el-icon :size="16"><Message /></el-icon>
              <span>邮箱</span>
            </div>
            <div class="form-control">
              <el-input v-model="form.email" placeholder="请输入邮箱地址" clearable>
                <template #prefix>
                  <el-icon><Message /></el-icon>
                </template>
              </el-input>
            </div>
          </div>

          <!-- 密码修改分隔 -->
          <div class="section-divider">
            <span class="divider-line" />
            <span class="divider-label">密码修改</span>
            <span class="divider-line" />
          </div>

          <!-- 新密码 -->
          <div class="form-row">
            <div class="form-label">
              <el-icon :size="16"><Lock /></el-icon>
              <span>新密码</span>
            </div>
            <div class="form-control">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="留空则不修改密码"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
              <p class="form-tip">至少 8 位字符</p>
            </div>
          </div>

          <!-- 确认密码 -->
          <div class="form-row">
            <div class="form-label">
              <el-icon :size="16"><Key /></el-icon>
              <span>确认密码</span>
            </div>
            <div class="form-control">
              <el-input
                v-model="form.confirmPassword"
                type="password"
                show-password
                placeholder="再次输入新密码"
              >
                <template #prefix>
                  <el-icon><Key /></el-icon>
                </template>
              </el-input>
            </div>
          </div>

          <!-- 提交按钮 -->
          <div class="form-actions">
            <el-button
              type="primary"
              :loading="saving"
              size="large"
              class="save-btn"
              @click="handleSave"
            >
              <el-icon v-if="!saving" :size="16"><Check /></el-icon>
              {{ saving ? '保存中...' : '保存修改' }}
            </el-button>
          </div>
        </el-form>
      </div>

      <!-- ── 账号信息 ── -->
      <div class="profile-card info-card">
        <div class="section-header">
          <el-icon :size="20"><InfoFilled /></el-icon>
          <span>账号信息</span>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <div class="info-icon-wrap">
              <el-icon :size="20"><UserFilled /></el-icon>
            </div>
            <div class="info-body">
              <span class="info-label">角色</span>
              <span class="info-value">{{ roleLabel }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon-wrap">
              <el-icon :size="20"><CircleCheck /></el-icon>
            </div>
            <div class="info-body">
              <span class="info-label">账号状态</span>
              <span class="info-value info-value--active">{{ user?.is_active ? '正常' : '已停用' }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon-wrap">
              <el-icon :size="20"><Clock /></el-icon>
            </div>
            <div class="info-body">
              <span class="info-label">登录时间</span>
              <span class="info-value">{{ formatDate(user?.last_login_at) }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon-wrap">
              <el-icon :size="20"><Calendar /></el-icon>
            </div>
            <div class="info-body">
              <span class="info-label">注册时间</span>
              <span class="info-value">{{ formatDate(user?.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  UserFilled,
  Message,
  Lock,
  Key,
  EditPen,
  InfoFilled,
  CircleCheck,
  RemoveFilled,
  Clock,
  Calendar,
  Check,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { updateProfile } from '@/api/auth'
import { formatDate } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'

const authStore = useAuthStore()
const formRef = ref()
const saving = ref(false)

const user = computed(() => authStore.user)

const userInitial = computed(() => {
  const name = user.value?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const roleLabel = computed(() => {
  const map: Record<string, string> = { viewer: '查看者', editor: '编辑者', admin: '管理员' }
  return map[user.value?.role || ''] || user.value?.role || '-'
})

const form = reactive({
  email: '',
  password: '',
  confirmPassword: '',
})

const rules: Record<string, any> = {
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirmPassword: [
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (value && value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

onMounted(() => {
  form.email = user.value?.email || ''
})

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload: Record<string, string> = {}
    if (form.email && form.email !== user.value?.email) {
      payload.email = form.email
    }
    if (form.password) {
      payload.password = form.password
    }
    if (!Object.keys(payload).length) {
      ElMessage.info('没有需要修改的内容')
      return
    }
    const updated = await updateProfile(payload)
    authStore.user = { ...authStore.user!, ...updated }
    ElMessage.success('个人信息已更新')
    form.password = ''
    form.confirmPassword = ''
  } catch {
    // handled by interceptor
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

// ── 页面布局 ──────────────────────────────────────────────────
.profile-view {
  display: flex;
  justify-content: center;
  padding: $spacing-lg 0 $spacing-xxl;
  min-height: 100%;
}

.profile-container {
  width: 100%;
  max-width: 800px;
  padding: 0 $spacing-xl;
}

// ── 卡片通用 ──────────────────────────────────────────────────
.profile-card {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-xxl $spacing-xxl;
  margin-bottom: $spacing-xl;
  transition: border-color $transition-normal, box-shadow $transition-normal;

  &:hover {
    border-color: rgba(var(--vs-accent-rgb), 0.3);
    box-shadow: 0 0 0 1px rgba(var(--vs-accent-rgb), 0.06);
  }
}

// ── 节标题 ────────────────────────────────────────────────────
.section-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: 17px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: $spacing-xxl;
  padding-bottom: $spacing-lg;
  border-bottom: 1px solid $border-color;

  .el-icon {
    color: $accent;
  }
}

// ── 头像卡片 ──────────────────────────────────────────────────
.avatar-card {
  display: flex;
  align-items: center;
  gap: $spacing-xxl;
  padding: $spacing-xxl $spacing-xxl;
  position: relative;
  overflow: hidden;
  border-left: 3px solid $accent;

  // 右侧装饰光晕
  &::before {
    content: '';
    position: absolute;
    top: -60%;
    right: -10%;
    width: 360px;
    height: 360px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(var(--vs-accent-rgb), 0.06), transparent 70%);
    pointer-events: none;
  }
}

.avatar-decoration {
  position: relative;
  flex-shrink: 0;
}

.avatar-ring {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, $accent, rgba(var(--vs-accent-rgb), 0.3));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.avatar-inner {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: $bg-secondary;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  font-size: 36px;
  font-weight: 700;
  color: $accent;
  line-height: 1;
  user-select: none;
}

.avatar-glow {
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--vs-accent-rgb), 0.15), transparent 70%);
  animation: pulse-glow 3s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.06); }
}

.avatar-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  position: relative;
  z-index: 1;
}

.avatar-name {
  font-size: 24px;
  font-weight: 700;
  color: $text-primary;
  margin: 0;
  line-height: 1.2;
}

.avatar-meta {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-wrap: wrap;
}

// ── 角色标签 ──────────────────────────────────────────────────
.role-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 14px;
  font-size: 13px;
  border-radius: 100px;
  font-weight: 500;
  line-height: 1.4;

  &.role--admin {
    color: $archived;
    background: rgba(var(--vs-archived-rgb), 0.12);
    border: 1px solid rgba(var(--vs-archived-rgb), 0.25);
  }
  &.role--editor {
    color: $accent;
    background: rgba(var(--vs-accent-rgb), 0.12);
    border: 1px solid rgba(var(--vs-accent-rgb), 0.25);
  }
  &.role--viewer {
    color: $text-secondary;
    background: rgba(var(--vs-text-secondary-rgb), 0.1);
    border: 1px solid rgba(var(--vs-text-secondary-rgb), 0.2);
  }
}

// ── 状态标签 ──────────────────────────────────────────────────
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  font-size: 13px;
  border-radius: 100px;
  font-weight: 500;
  line-height: 1.4;

  &.status--active {
    color: $active;
    background: rgba(var(--vs-active-rgb), 0.1);
    border: 1px solid rgba(var(--vs-active-rgb), 0.2);
  }
  &.status--disabled {
    color: $critical;
    background: rgba(var(--vs-critical-rgb), 0.1);
    border: 1px solid rgba(var(--vs-critical-rgb), 0.2);
  }
}

// ── 表单 ──────────────────────────────────────────────────────
.form-card {
  padding: $spacing-xxl $spacing-xxl;
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-xxl;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: $font-body;
  font-weight: 500;
  color: $text-secondary;

  .el-icon {
    color: $text-disabled;
  }
}

.form-control {
  :deep(.el-input) {
    height: 42px;

    .el-input__wrapper {
      background-color: $bg-tertiary;
    }
  }

  :deep(.el-input.is-disabled) {
    .el-input__wrapper {
      background-color: $bg-secondary;
    }
  }
}

.form-tip {
  font-size: $font-caption;
  color: $text-disabled;
  margin: $spacing-xs 0 0;
  line-height: 1.4;
}

// ── 分隔线 ────────────────────────────────────────────────────
.section-divider {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm 0;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: $border-color;
}

.divider-label {
  font-size: 13px;
  color: $text-disabled;
  white-space: nowrap;
  font-weight: 500;
  letter-spacing: 0.5px;
}

// ── 提交按钮 ──────────────────────────────────────────────────
.form-actions {
  display: flex;
  justify-content: flex-start;
  padding-top: $spacing-sm;
}

.save-btn {
  min-width: 180px;
  font-weight: 500;
  letter-spacing: 0.5px;
  padding: 12px 32px;
  height: 44px;
  font-size: 15px;
  border-radius: $radius-md;

  .el-icon {
    margin-right: 4px;
  }
}

// ── 账号信息卡片 ──────────────────────────────────────────────
.info-card {
  position: relative;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-lg;
}

.info-item {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  padding: $spacing-lg $spacing-xl;
  background: $bg-tertiary;
  border-radius: $radius-md;
  border: 1px solid $border-subtle;
  transition: border-color $transition-fast, background-color $transition-fast;

  &:hover {
    border-color: rgba(var(--vs-accent-rgb), 0.2);
    background: rgba(var(--vs-accent-rgb), 0.03);
  }
}

.info-icon-wrap {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-md;
  background: rgba(var(--vs-accent-rgb), 0.08);
  color: $accent;
  flex-shrink: 0;
}

.info-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.info-label {
  font-size: 13px;
  color: $text-disabled;
  line-height: 1.3;
}

.info-value {
  font-size: 15px;
  font-weight: 500;
  color: $text-primary;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  &.info-value--active {
    color: $active;
  }
}

// ── 响应式 ────────────────────────────────────────────────────
@media (max-width: 600px) {
  .profile-container {
    padding: 0 $spacing-lg;
  }

  .avatar-card {
    flex-direction: column;
    text-align: center;
    gap: $spacing-lg;
    padding: $spacing-xl $spacing-lg;

    &::before {
      display: none;
    }
  }

  .avatar-meta {
    justify-content: center;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    justify-content: center;
  }

  .save-btn {
    width: 100%;
  }
}
</style>