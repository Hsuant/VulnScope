<template>
  <div class="login-view">
    <!-- 动态背景网格 -->
    <div class="bg-grid">
      <div class="grid-line horizontal" v-for="i in 12" :key="'h' + i" :style="{ top: `${i * 8.33}%` }" />
      <div class="grid-line vertical" v-for="i in 12" :key="'v' + i" :style="{ left: `${i * 8.33}%` }" />
    </div>
    <div class="bg-glow" />
    <div class="bg-dots">
      <span v-for="i in 40" :key="'d' + i" class="dot" :style="randomDotStyle(i)" />
    </div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <svg viewBox="0 0 32 32" fill="none" width="44" height="44">
            <path d="M16 2L4 8v6c0 6.5 4.5 12.5 12 16 7.5-3.5 12-9.5 12-16V8L16 2z" fill="#4a8cba" opacity="0.9"/>
            <path d="M16 6l-8 4v4.5c0 4.7 3.2 9 8 11.5 4.8-2.5 8-6.8 8-11.5V10l-8-4z" fill="#0e0e10" stroke="#4a8cba" stroke-width="0.5"/>
            <path d="M16 10l-4 2v3c0 2.8 1.8 5.3 4 6.5 2.2-1.2 4-3.7 4-6.5v-3l-4-2z" fill="#4a8cba" opacity="0.6"/>
          </svg>
        </div>
        <h1 class="login-title">VulnScope</h1>
        <p class="login-subtitle">POC 漏洞验证脚本管理系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <p class="login-hint">默认管理员账号: admin / admin123</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function randomDotStyle(i: number) {
  const x = ((i * 17 + 5) % 100)
  const y = ((i * 31 + 13) % 100)
  const delay = (i * 0.15) % 4
  const size = 2 + (i % 3)
  return {
    left: `${x}%`,
    top: `${y}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
    opacity: 0.2 + (i % 5) * 0.1,
  }
}

async function handleLogin() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
    ElMessage.success('登录成功')
  } catch (err: any) {
    // 错误由拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.login-view {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: $bg-primary;
}

// ── 动态网格背景 ──────────────────────────────────────────────
.bg-grid {
  position: absolute;
  inset: 0;
  perspective: 600px;
  transform: rotateX(40deg);
  transform-origin: center center;
  opacity: 0.15;
}

.grid-line {
  position: absolute;
  background: $accent;

  &.horizontal {
    left: 0;
    right: 0;
    height: 1px;
  }

  &.vertical {
    top: 0;
    bottom: 0;
    width: 1px;
  }
}

.bg-glow {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--vs-accent-rgb), 0.06) 0%, transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.bg-dots {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.dot {
  position: absolute;
  border-radius: 50%;
  background: $accent;
  animation: dotPulse 4s ease-in-out infinite;
}

@keyframes dotPulse {
  0%, 100% { opacity: 0.1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.5); }
}

// ── 登录卡片 ──────────────────────────────────────────────────
.login-card {
  position: relative;
  z-index: 1;
  width: 400px;
  background: rgba(var(--vs-bg-secondary), 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid $border-color;
  border-radius: 12px;
  padding: 40px 36px;
  box-shadow:
    0 0 0 1px rgba(var(--vs-accent-rgb), 0.05),
    0 8px 32px var(--vs-login-card-shadow);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, $accent, transparent);
    opacity: 0.4;
    border-radius: 12px 12px 0 0;
  }
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.login-title {
  font-size: 26px;
  font-weight: 700;
  color: $text-primary;
  margin: 0 0 6px;
  letter-spacing: 1.5px;
}

.login-subtitle {
  font-size: $font-body;
  color: $text-secondary;
  margin: 0;
}

.login-form {
  margin-bottom: 20px;

  :deep(.el-form-item) {
    margin-bottom: 20px;
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  letter-spacing: 0.5px;
}

.login-hint {
  text-align: center;
  font-size: $font-caption;
  color: $text-disabled;
  margin: 0;
}
</style>