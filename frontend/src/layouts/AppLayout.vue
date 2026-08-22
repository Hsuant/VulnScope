<template>
  <div class="app-layout">
    <SidebarNav :collapsed="appStore.sidebarCollapsed" />
    <div class="main-area" :class="{ collapsed: appStore.sidebarCollapsed }">
      <TopBar :collapsed="appStore.sidebarCollapsed" />
      <main class="content">
        <router-view v-slot="{ Component, route }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import TopBar from '@/components/layout/TopBar.vue'

const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()

onMounted(async () => {
  if (authStore.isAuthenticated && !authStore.user) {
    try {
      await authStore.fetchCurrentUser()
    } catch {
      authStore.logout()
      router.push('/login')
    }
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: margin-left $transition-normal;
}

.content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: $spacing-xl;
  background: $bg-primary;
  transition: background-color 0.3s ease;
}
</style>
