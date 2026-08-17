<template>
  <div class="vuln-import-view">
    <PageHeader title="导入 CVE" description="批量导入 CVE 漏洞库数据，支持从外部源文件同步漏洞信息" />

    <!-- 功能预留占位：后续迭代接入导入流程实现 -->
    <EmptyState
      icon="Upload"
      title="功能预留"
      description="导入 CVE 功能尚未开放，当前版本仅支持查看与删除 CVE 漏洞数据。"
      :action="{ label: '返回 CVE 列表', handler: goToList }"
    />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()

/** 返回 CVE 列表页。 */
function goToList() {
  router.push('/vulns')
}
</script>

<style scoped lang="scss">
.vuln-import-view {
  height: 100%;
}
</style>