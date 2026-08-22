<template>
  <div class="comment-section">
    <h3 class="section-title">{{ $t('comment.titleWithCount', { count: comments.length }) }}</h3>

    <!-- 输入框 -->
    <div class="comment-input-wrap">
      <el-input
        v-model="newContent"
        type="textarea"
        :rows="3"
        :placeholder="$t('comment.placeholder')"
        :disabled="submitting"
        maxlength="10000"
        show-word-limit
      />
      <div class="input-actions">
        <el-button type="primary" size="small" :loading="submitting" @click="handleCreate">
          {{ $t('comment.send') }}
        </el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <EmptyState v-if="!comments.length" :title="$t('comment.empty')" />

    <!-- 评论列表 -->
    <div v-else class="comment-list">
      <div v-for="comment in comments" :key="comment.id" class="comment-item">
        <CommentCard
          :comment="comment"
          :poc-id="pocId"
          @refresh="loadComments"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { listComments, createComment, type CommentItem } from '@/api/comment'
import CommentCard from './CommentCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const props = defineProps<{ pocId: number }>()

const { t } = useI18n()

const comments = ref<CommentItem[]>([])
const newContent = ref('')
const submitting = ref(false)

onMounted(() => {
  loadComments()
})

async function loadComments() {
  try {
    comments.value = await listComments(props.pocId)
  } catch {
    // 静默处理
  }
}

async function handleCreate() {
  const content = newContent.value.trim()
  if (!content) {
    ElMessage.warning(t('comment.messages.contentRequired'))
    return
  }
  submitting.value = true
  try {
    comments.value = await createComment(props.pocId, { content })
    newContent.value = ''
    ElMessage.success(t('comment.createSuccess'))
  } catch {
    ElMessage.error(t('comment.messages.sendError'))
  } finally {
    submitting.value = false
  }
}

defineExpose({ loadComments })
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.comment-section {
  margin-top: $spacing-xxl;
  padding-top: $spacing-xl;
  border-top: 1px solid $border-color;
}

.section-title {
  font-size: $font-title;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-lg;
}

.comment-input-wrap {
  margin-bottom: $spacing-xl;

  .input-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: $spacing-sm;
  }
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}
</style>