<template>
  <div class="topbar">
    <div class="topbar-left">
      <el-button class="collapse-btn" :icon="collapsed ? 'Expand' : 'Fold'" text @click="appStore.toggleSidebar" />
    </div>
    <div class="topbar-right">
      <!-- 主题切换：主按钮点击在 light→dark→system 间循环切换图标；
           右侧下拉箭头可直接选定目标模式。 -->
      <div class="theme-group">
        <el-tooltip :content="themeTooltip" placement="bottom" :show-after="300">
          <el-button class="theme-btn" text @click="appStore.toggleTheme">
            <el-icon :size="18">
              <Sunny v-if="appStore.themeMode === 'light'" />
              <Monitor v-else-if="appStore.themeMode === 'system'" />
              <Moon v-else />
            </el-icon>
          </el-button>
        </el-tooltip>
        <el-dropdown trigger="click" @command="(c: string) => appStore.setThemeMode(c as ThemeMode)">
          <el-button class="theme-mode-btn" text>
            <el-icon :size="12"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="light" :class="{ active: appStore.themeMode === 'light' }">
                <el-icon><Sunny /></el-icon> {{ $t('common.theme.light') }}
              </el-dropdown-item>
              <el-dropdown-item command="dark" :class="{ active: appStore.themeMode === 'dark' }">
                <el-icon><Moon /></el-icon> {{ $t('common.theme.dark') }}
              </el-dropdown-item>
              <el-dropdown-item command="system" :class="{ active: appStore.themeMode === 'system' }">
                <el-icon><Monitor /></el-icon> {{ $t('common.theme.system') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 语言切换：按钮显示当前语言的国旗（flag-icons） -->
      <el-dropdown trigger="click" @command="handleLocaleChange">
        <el-button class="locale-btn" text>
          <span class="fi locale-flag" :class="flagClass(locale)"></span>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="zh-CN" :class="{ active: locale === 'zh-CN' }">
              <span class="fi fi-cn locale-flag-mini"></span> 中文
            </el-dropdown-item>
            <el-dropdown-item command="en" :class="{ active: locale === 'en' }">
              <span class="fi fi-gb locale-flag-mini"></span> English
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <!-- 用户信息 -->
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-info">
          <span class="user-avatar">{{ userInitial }}</span>
          <span class="user-name">{{ authStore.user?.username || $t('common.user.fallbackName') }}</span>
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>{{ $t('common.user.profile') }}
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>{{ $t('common.user.logout') }}
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
import { useI18n } from 'vue-i18n'
import 'flag-icons/css/flag-icons.min.css'
import { useAuthStore } from '@/stores/auth'
import { useAppStore, type ThemeMode } from '@/stores/app'
import { setStoredLocale, type AppLocale } from '@/i18n'
import { Sunny, Moon, Monitor, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps<{ collapsed: boolean }>()

const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const { t, locale } = useI18n()

// locale → ISO 国家码（用于 flag-icons 的国旗 sprite：en→gb, zh-CN→cn）
const LOCALE_FLAG: Record<string, string> = { 'zh-CN': 'cn', en: 'gb' }
function flagClass(loc: string): string {
  return `fi-${LOCALE_FLAG[loc] || 'cn'}`
}

const userInitial = computed(() => {
  const name = authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const themeTooltip = computed(() => {
  // 提示「当前模式 · 点击切换至下一模式」，循环顺序 light→dark→system→light
  const order: ThemeMode[] = ['light', 'dark', 'system']
  const cur = appStore.themeMode
  const next = order[(order.indexOf(cur) + 1) % order.length]
  const curLabel = t(`common.theme.${cur}`)
  const nextLabel = t(`common.theme.${next}`)
  return `${curLabel} · ${t('common.theme.clickToSwitch', { next: nextLabel })}`
})

function handleLocaleChange(loc: string) {
  const next = (['zh-CN', 'en'] as AppLocale[]).includes(loc as AppLocale) ? (loc as AppLocale) : 'zh-CN'
  locale.value = next
  setStoredLocale(next)
}

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

// 主题切换组合：主按钮（点击循环切换图标）+ 下拉箭头（直选模式）
.theme-group {
  display: inline-flex;
  align-items: center;
  margin-right: $spacing-xs;
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
  font-size: 12px;
  color: $text-disabled;
  padding: 0 2px;
  transition: color $transition-fast;

  &:hover {
    color: $text-secondary;
  }
}

.locale-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: $spacing-xs $spacing-sm;
  border-radius: $radius-md;
  color: $text-disabled;
  transition: color $transition-fast, background $transition-fast;

  &:hover {
    color: $text-secondary;
    background: rgba(var(--vs-accent-rgb), 0.08);
  }
}

// 国旗（flag-icons）：按钮内大号、下拉项内小号
.locale-flag {
  font-size: 18px;
  line-height: 1;
  vertical-align: middle;
}

.locale-flag-mini {
  font-size: 14px;
  line-height: 1;
  margin-right: $spacing-xs;
  vertical-align: middle;
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