<template>
  <div class="sidebar" :class="{ collapsed }">
    <div class="logo">
      <div class="logo-icon">
        <svg viewBox="0 0 32 32" fill="none">
          <path d="M16 2L4 8v6c0 6.5 4.5 12.5 12 16 7.5-3.5 12-9.5 12-16V8L16 2z" fill="#4a8cba" opacity="0.9"/>
          <path d="M16 6l-8 4v4.5c0 4.7 3.2 9 8 11.5 4.8-2.5 8-6.8 8-11.5V10l-8-4z" fill="var(--vs-bg-primary)" stroke="#4a8cba" stroke-width="0.5"/>
          <path d="M16 10l-4 2v3c0 2.8 1.8 5.3 4 6.5 2.2-1.2 4-3.7 4-6.5v-3l-4-2z" fill="#4a8cba" opacity="0.6"/>
        </svg>
      </div>
      <span v-show="!collapsed" class="logo-text">VulnScope</span>
    </div>

    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      :collapse-transition="false"
      router
      class="nav-menu"
    >
      <el-menu-item index="/dashboard">
        <el-icon><Grid /></el-icon>
        <template #title>工作台</template>
      </el-menu-item>

      <el-sub-menu index="/pocs">
        <template #title>
          <el-icon><Document /></el-icon>
          <span>POC 管理</span>
        </template>
        <el-menu-item index="/pocs">POC 列表</el-menu-item>
        <el-menu-item v-if="canEdit" index="/pocs/new">新建 POC</el-menu-item>
        <el-menu-item v-if="canEdit" index="/pocs/import">导入 POC</el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="/vulns">
        <template #title>
          <el-icon><Warning /></el-icon>
          <span>CVE 漏洞库</span>
        </template>
        <el-menu-item index="/vulns">CVE 列表</el-menu-item>
        <el-menu-item v-if="canEdit" index="/vulns/new">新建 CVE</el-menu-item>
        <el-menu-item v-if="canEdit" index="/vulns/import">导入 CVE</el-menu-item>
      </el-sub-menu>

      <el-menu-item index="/tags">
        <el-icon><Collection /></el-icon>
        <template #title>标签管理</template>
      </el-menu-item>

      <el-menu-item index="/plugins">
        <el-icon><Setting /></el-icon>
        <template #title>插件面板</template>
      </el-menu-item>

      <el-sub-menu v-if="isAdmin" index="/system">
        <template #title>
          <el-icon><Tools /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item index="/system/users">用户管理</el-menu-item>
        <el-menu-item index="/system/audit-logs">审计日志</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { usePermission } from '@/composables/usePermission'

defineProps<{ collapsed: boolean }>()

const route = useRoute()
const appStore = useAppStore()
const { canEdit, isAdmin } = usePermission()

const activeMenu = computed(() => {
  const path = route.path
  // 子页面（新建/导入）高亮时，折叠父级菜单项保持展开状态
  if (path.startsWith('/pocs')) return path.startsWith('/pocs/new') || path.startsWith('/pocs/import') ? '/pocs' : path
  if (path.startsWith('/vulns')) return path.startsWith('/vulns/new') || path.startsWith('/vulns/import') ? '/vulns' : path
  return path
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.sidebar {
  width: $sidebar-width;
  height: 100vh;
  background: $bg-tertiary;
  border-right: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  transition: width $transition-normal, background-color 0.3s ease, border-color 0.3s ease;
  overflow: hidden;
  flex-shrink: 0;

  &.collapsed {
    width: $sidebar-collapsed;
  }
}

.logo {
  height: $topbar-height;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid $border-color;
  gap: 12px;
  flex-shrink: 0;
}

.logo-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;

  svg {
    width: 100%;
    height: 100%;
  }
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

// ── 导航菜单 ──────────────────────────────────────────────────
.nav-menu {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
  border: none;
  background: transparent;

  // 一级菜单项
  :deep(.el-menu-item) {
    display: flex;
    align-items: center;
    height: 42px;
    line-height: 42px;
    padding: 0 12px !important;
    margin: 2px 8px;
    border-radius: 6px;
    color: $text-secondary;
    font-size: 14px;

    .el-icon {
      font-size: 18px;
      margin-right: 8px;
      flex-shrink: 0;
      color: $text-secondary;
    }

    &:hover {
      background-color: rgba($accent, 0.08);
      color: $text-primary;

      .el-icon {
        color: $text-primary;
      }
    }

    &.is-active {
      background-color: rgba($accent, 0.15);
      color: $accent;

      .el-icon {
        color: $accent;
      }
    }
  }

  // 子菜单标题
  :deep(.el-sub-menu) {
    .el-sub-menu__title {
      display: flex;
      align-items: center;
      height: 42px;
      line-height: 42px;
      padding: 0 12px !important;
      margin: 2px 8px;
      border-radius: 6px;
      color: $text-secondary;
      font-size: 14px;

      .el-icon {
        font-size: 18px;
        margin-right: 8px;
        flex-shrink: 0;
        color: $text-secondary;
      }

      &:hover {
        background-color: rgba($accent, 0.08);
        color: $text-primary;

        .el-icon {
          color: $text-primary;
        }
      }
    }

    // 子菜单项
    .el-menu {
      background: transparent;
      padding: 0;

      .el-menu-item {
        padding-left: 44px !important;
        height: 36px;
        line-height: 36px;
        margin: 1px 8px;
        font-size: 13px;
      }
    }
  }

  // 折叠模式
  .el-menu--collapse & {
    :deep(.el-menu-item) {
      padding: 0 !important;
      margin: 2px 6px;
      justify-content: center;

      .el-icon {
        margin-right: 0;
      }
    }

    :deep(.el-sub-menu) {
      .el-sub-menu__title {
        padding: 0 !important;
        margin: 2px 6px;
        justify-content: center;

        .el-icon {
          margin-right: 0;
        }
      }
    }
  }
}
</style>