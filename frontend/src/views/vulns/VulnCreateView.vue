<template>
  <div class="vuln-create-view">
    <PageHeader title="新建 CVE" description="登记新的 CVE 漏洞信息，包含编号、标题、级别与 CVSS 评分" />

    <!-- 功能预留占位：后续迭代接入表单实现 -->
    <EmptyState
      icon="Plus"
      title="功能预留"
      description="新建 CVE 功能尚未开放，当前版本仅支持查看与删除 CVE 漏洞数据。"
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
.vuln-create-view {
  height: 100%;
}
</style>