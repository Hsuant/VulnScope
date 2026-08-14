<template>
  <div class="error-page">
    <div class="error-content">
      <h1 class="error-code">404</h1>
      <h2 class="error-title">页面不存在</h2>
      <p class="error-desc">您访问的页面不存在或已被移除</p>
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