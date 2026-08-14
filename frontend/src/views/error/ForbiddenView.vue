<template>
  <div class="error-page">
    <div class="error-content">
      <h1 class="error-code">403</h1>
      <h2 class="error-title">权限不足</h2>
      <p class="error-desc">您没有访问此页面的权限，请联系管理员</p>
      <el-button type="primary" @click="$router.push('/dashboard')">返回工作台</el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.error-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-content {
  text-align: center;
}

.error-code {
  font-size: 96px;
  font-weight: 700;
  color: $accent;
  opacity: 0.5;
  margin: 0 0 $spacing-md;
  line-height: 1;
}

.error-title {
  font-size: 24px;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-sm;
}

.error-desc {
  color: $text-secondary;
  margin: 0 0 $spacing-xl;
}
</style>