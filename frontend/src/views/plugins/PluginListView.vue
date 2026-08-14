<template>
  <div class="plugin-list-view">
    <PageHeader title="插件面板" description="已注册的插件列表及运行状态" />

    <div v-loading="loading" class="plugin-content">
      <div v-for="group in pluginGroups" :key="group.slot" class="plugin-group">
        <h3 class="group-title">{{ groupLabel(group.slot) }}</h3>
        <div v-if="group.plugins.length" class="plugin-cards">
          <div v-for="plug in group.plugins" :key="plug.name" class="plugin-card">
            <div class="plugin-info">
              <span class="plugin-name">{{ plug.name }}</span>
              <span class="plugin-version">v{{ plug.version }}</span>
            </div>
            <span class="plugin-status" :class="{ enabled: plug.enabled }">
              <span class="status-dot" />
              {{ plug.enabled ? '已启用' : '已禁用' }}
            </span>
          </div>
        </div>
        <div v-else class="empty-slot">
          <span class="empty-text">暂无注册插件</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listPlugins } from '@/api/plugin'
import PageHeader from '@/components/common/PageHeader.vue'
import type { PluginItem } from '@/types/plugin'

const loading = ref(true)
const plugins = ref<PluginItem[]>([])

const pluginGroups = computed(() => {
  const map = new Map<string, PluginItem[]>()
  for (const p of plugins.value) {
    if (!map.has(p.slot)) map.set(p.slot, [])
    map.get(p.slot)!.push(p)
  }
  return Array.from(map.entries()).map(([slot, items]) => ({ slot, plugins: items }))
})

const slotLabels: Record<string, string> = {
  parser: 'Parser 解析器',
  source: 'Source 来源',
  verifier: 'Verifier 验证引擎',
  exporter: 'Exporter 导出器',
  consumer: 'EventConsumer 事件消费者',
}

function groupLabel(slot: string): string {
  return slotLabels[slot] || slot
}

async function loadData() {
  loading.value = true
  try {
    plugins.value = await listPlugins()
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.plugin-content {
  display: flex;
  flex-direction: column;
  gap: $spacing-xl;
}

.plugin-group {
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
}

.group-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  padding: $spacing-lg;
  margin: 0;
  border-bottom: 1px solid $border-color;
}

.plugin-cards {
  padding: $spacing-lg;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.plugin-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  border: 1px solid $border-subtle;
  border-radius: $radius-sm;
  transition: border-color $transition-fast;

  &:hover {
    border-color: $border-color;
  }
}

.plugin-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.plugin-name {
  font-size: $font-body;
  color: $text-primary;
  font-weight: 500;
}

.plugin-version {
  font-size: $font-caption;
  color: $text-disabled;
}

.plugin-status {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-size: $font-caption;
  color: $text-disabled;

  &.enabled {
    color: $active;
  }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.empty-slot {
  padding: $spacing-lg;
  text-align: center;
}

.empty-text {
  color: $text-disabled;
  font-size: $font-body;
}
</style>