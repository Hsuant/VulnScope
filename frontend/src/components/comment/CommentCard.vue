<template>
  <div class="comment-card" :class="{ deleted: comment.deleted, 'has-replies': comment.replies?.length }">
    <div class="comment-header">
      <span class="comment-author">{{ comment.username }}</span>
      <span class="comment-time">{{ formatRelativeTime(comment.created_at) }}</span>
      <span v-if="comment.edited && !comment.deleted" class="edited-tag">{{ $t('comment.edited') }}</span>
    </div>
    <div class="comment-body">
      <p v-if="!editing" class="comment-content">{{ comment.content }}</p>
      <div v-else class="edit-wrap">
        <el-input
          v-model="editContent"
          type="textarea"
          :rows="2"
          maxlength="10000"
          show-word-limit
        />
        <div class="edit-actions">
          <el-button size="small" @click="cancelEdit">{{ $t('comment.cancel') }}</el-button>
          <el-button size="small" type="primary" :loading="editingSubmit" @click="saveEdit">
            {{ $t('comment.save') }}
          </el-button>
        </div>
      </div>
    </div>
    <div v-if="!comment.deleted" class="comment-actions">
      <el-button v-if="!editing" text size="small" @click="startReply">
        {{ $t('comment.reply') }}
      </el-button>
      <el-button v-if="!editing && isOwner" text size="small" @click="startEdit">
        {{ $t('comment.edit') }}
      </el-button>
      <el-button v-if="!editing && isOwner" text size="small" type="danger" @click="handleDelete">
        {{ $t('comment.delete') }}
      </el-button>
    </div>

    <!-- 回复输入框 -->
    <div v-if="showReply" class="reply-input-wrap">
      <el-input
        v-model="replyContent"
        type="textarea"
        :rows="2"
        :placeholder="$t('comment.replyTo', { username: comment.username })"
        maxlength="10000"
      />
      <div class="reply-actions">
        <el-button size="small" @click="cancelReply">{{ $t('comment.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="replySubmitting" @click="submitReply">
          {{ $t('comment.send') }}
        </el-button>
      </div>
    </div>

    <!-- 子回复 -->
    <div v-if="comment.replies?.length" class="reply-list">
      <div v-for="reply in comment.replies" :key="reply.id" class="reply-item">
        <div class="reply-header">
          <span class="comment-author">{{ reply.username }}</span>
          <span class="comment-time">{{ formatRelativeTime(reply.created_at) }}</span>
          <span v-if="reply.edited && !reply.deleted" class="edited-tag">{{ $t('comment.edited') }}</span>
        </div>
        <div class="reply-body">
          <p class="comment-content">{{ reply.content }}</p>
        </div>
        <div v-if="!reply.deleted" class="reply-actions-row">
          <el-button
            v-if="isReplyOwner(reply)"
            text
            size="small"
            type="danger"
            @click="handleDeleteReply(reply)"
          >
            {{ $t('comment.delete') }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { updateComment, deleteComment, createComment, type CommentItem } from '@/api/comment'
import { useAuthStore } from '@/stores/auth'
import { formatRelativeTime } from '@/utils/format'

const props = defineProps<{
  comment: CommentItem
  pocId: number
}>()

const emit = defineEmits<{ refresh: [] }>()

const { t } = useI18n()
const authStore = useAuthStore()

const editing = ref(false)
const editContent = ref('')
const editingSubmit = ref(false)
const showReply = ref(false)
const replyContent = ref('')
const replySubmitting = ref(false)

const isOwner = computed(() => authStore.user?.id === props.comment.user_id)

function isReplyOwner(reply: CommentItem) {
  return authStore.user?.id === reply.user_id
}

function startEdit() {
  editContent.value = props.comment.content
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editContent.value = ''
}

async function saveEdit() {
  const content = editContent.value.trim()
  if (!content) return
  editingSubmit.value = true
  try {
    await updateComment(props.comment.id, { content })
    ElMessage.success(t('comment.editSuccess'))
    editing.value = false
    emit('refresh')
  } catch {
    ElMessage.error(t('comment.messages.sendError'))
  } finally {
    editingSubmit.value = false
  }
}

function startReply() {
  replyContent.value = ''
  showReply.value = true
}

function cancelReply() {
  showReply.value = false
  replyContent.value = ''
}

async function submitReply() {
  const content = replyContent.value.trim()
  if (!content) return
  replySubmitting.value = true
  try {
    await createComment(props.pocId, { content, parent_id: props.comment.id })
    ElMessage.success(t('comment.createSuccess'))
    showReply.value = false
    replyContent.value = ''
    emit('refresh')
  } catch {
    ElMessage.error(t('comment.messages.sendError'))
  } finally {
    replySubmitting.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(t('comment.deleteConfirm'), t('common.title.confirm'), {
      confirmButtonText: t('common.action.delete'),
      cancelButtonText: t('common.action.cancel'),
      type: 'warning',
    })
    await deleteComment(props.comment.id)
    ElMessage.success(t('comment.deleteSuccess'))
    emit('refresh')
  } catch {
    // 取消或失败
  }
}

async function handleDeleteReply(reply: CommentItem) {
  try {
    await ElMessageBox.confirm(t('comment.deleteConfirm'), t('common.title.confirm'), {
      confirmButtonText: t('common.action.delete'),
      cancelButtonText: t('common.action.cancel'),
      type: 'warning',
    })
    await deleteComment(reply.id)
    ElMessage.success(t('comment.deleteSuccess'))
    emit('refresh')
  } catch {
    // 取消或失败
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.comment-card {
  padding: $spacing-md;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: $bg-secondary;
  transition: background-color 0.3s ease;

  &.deleted {
    opacity: 0.6;
  }
}

.comment-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-xs;
}

.comment-author {
  font-weight: 600;
  font-size: $font-body;
  color: $accent;
}

.comment-time {
  font-size: $font-caption;
  color: $text-disabled;
}

.edited-tag {
  font-size: $font-caption;
  color: $text-disabled;
  font-style: italic;
}

.comment-body {
  margin-bottom: $spacing-xs;
}

.comment-content {
  margin: 0;
  font-size: $font-body;
  color: $text-primary;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.edit-wrap {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-xs;
}

.comment-actions {
  display: flex;
  gap: $spacing-xs;
}

.reply-input-wrap {
  margin-top: $spacing-sm;
  padding: $spacing-sm;
  background: $bg-primary;
  border-radius: $radius-md;

  .reply-actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-xs;
    margin-top: $spacing-xs;
  }
}

.reply-list {
  margin-top: $spacing-sm;
  padding-left: $spacing-lg;
  border-left: 2px solid $border-color;

  .reply-item {
    padding: $spacing-sm 0;

    .reply-header {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      margin-bottom: 2px;
    }

    .reply-body {
      .comment-content {
        font-size: $font-body;
      }
    }

    .reply-actions-row {
      margin-top: 2px;
    }
  }
}
</style>