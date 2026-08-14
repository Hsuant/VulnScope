<template>
  <div class="topbar">
    <div class="topbar-left">
      <el-button class="collapse-btn" :icon="collapsed ? 'Expand' : 'Fold'" text @click="appStore.toggleSidebar" />
    </div>
    <div class="topbar-right">
      <!-- 主题切换 -->
      <el-tooltip :content="themeTooltip" placement="bottom" :show-after="300">
        <el-button class="theme-btn" text @click="appStore.toggleTheme">
          <el-icon :size="18">
            <Sunny v-if="appStore.resolvedTheme === 'light'" />
            <Moon v-else />
          </el-icon>
        </el-button>
      </el-tooltip>

      <!-- 主题模式下拉：细化选择 light / dark / system -->
      <el-dropdown trigger="click" @command="appStore.setThemeMode">
        <el-button class="theme-mode-btn" text>
          <el-icon :size="14"><Setting /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="light" :class="{ active: appStore.themeMode === 'light' }">
              <el-icon><Sunny /></el-icon> 白天模式
            </el-dropdown-item>
            <el-dropdown-item command="dark" :class="{ active: appStore.themeMode === 'dark' }">
              <el-icon><Moon /></el-icon> 黑夜模式
            </el-dropdown-item>
            <el-dropdown-item command="system" :class="{ active: appStore.themeMode === 'system' }">
              <el-icon><Monitor /></el-icon> 跟随系统
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <!-- 用户信息 -->
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-info">
          <span class="user-avatar">{{ userInitial }}</span>
          <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>个人信息
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { Sunny, Moon, Monitor, Setting } from '@element-plus/icons-vue'

const props = defineProps<{ collapsed: boolean }>()

const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()

const userInitial = computed(() => {
  const name = authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const themeTooltip = computed(() => {
  if (appStore.resolvedTheme === 'light') return '切换为深色模式'
  return '切换为浅色模式'
})

function handleCommand(cmd: string) {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.topbar {
  height: $topbar-height;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $spacing-lg;
  border-bottom: 1px solid $border-color;
  background: $bg-secondary;
  flex-shrink: 0;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.collapse-btn {
  font-size: 18px;
  color: $text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $accent;
  }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.theme-btn {
  font-size: 18px;
  color: $text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $accent;
  }
}

.theme-mode-btn {
  font-size: 14px;
  color: $text-disabled;
  transition: color $transition-fast;

  &:hover {
    color: $text-secondary;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  cursor: pointer;
  padding: $spacing-xs $spacing-sm;
  border-radius: $radius-md;
  transition: background $transition-fast;

  &:hover {
    background: rgba(var(--vs-accent-rgb), 0.08);
  }
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: $accent;
  color: $text-inverse;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-caption;
  font-weight: 600;
}

.user-name {
  font-size: $font-body;
  color: $text-primary;
}
</style>