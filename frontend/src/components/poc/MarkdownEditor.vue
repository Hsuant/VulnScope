<template>
  <div class="md-editor">
    <!-- 工具栏 -->
    <div class="md-toolbar">
      <button class="md-btn" :title="$t('markdownEditor.toolbar.heading')" @click="insertHeading">H</button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.bold')" @click="wrapBold"><b>B</b></button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.italic')" @click="wrapItalic"><i>I</i></button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.strike')" @click="wrapStrike"><s>S</s></button>
      <span class="md-sep" />
      <button class="md-btn" :title="$t('markdownEditor.toolbar.unorderedList')" @click="insertList(false)">{{ $t('markdownEditor.toolbar.listBullet') }}</button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.orderedList')" @click="insertList(true)">{{ $t('markdownEditor.toolbar.listOrdered') }}</button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.quote')" @click="insertQuote">{{ $t('markdownEditor.toolbar.quoteMark') }}</button>
      <span class="md-sep" />
      <button class="md-btn" :title="$t('markdownEditor.toolbar.inlineCode')" @click="wrapInlineCode">&lt;/&gt;</button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.codeBlock')" @click="wrapCodeBlock">{ }</button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.link')" @click="insertLink">🔗</button>
      <button class="md-btn" :title="$t('markdownEditor.toolbar.table')" @click="insertTable">▦</button>
      <span class="md-sep" />
      <button class="md-btn" :title="$t('markdownEditor.toolbar.hr')" @click="insertHr">—</button>
    </div>

    <!-- 编辑 / 预览分栏 -->
    <div class="md-split">
      <div class="md-edit-pane">
        <textarea
          ref="taRef"
          :value="modelValue"
          class="md-textarea"
          spellcheck="false"
          :placeholder="$t('markdownEditor.placeholder')"
          @input="onInput"
        />
      </div>
      <div class="md-preview-pane">
        <div class="md-preview-label">{{ $t('markdownEditor.preview') }}</div>
        <div class="md-preview-scroll">
          <MarkdownRenderer :content="modelValue" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MarkdownRenderer from './MarkdownRenderer.vue'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const { t } = useI18n()

const taRef = ref<HTMLTextAreaElement>()

// 特殊字符集中在 script 中，避免模板属性值解析歧义
const FENCE = '```'
const NL = '\n'

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
}

function emitAndUpdate(next: string, selStart: number, selEnd: number) {
  emit('update:modelValue', next)
  const ta = taRef.value
  if (!ta) return
  requestAnimationFrame(() => {
    ta.focus()
    ta.setSelectionRange(selStart, selEnd)
  })
}

// 在选区两侧包裹成对标记
function wrap(before: string, placeholder: string) {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, selectionEnd: e, value } = ta
  const selected = value.slice(s, e) || placeholder
  const next = value.slice(0, s) + before + selected + before + value.slice(e)
  emitAndUpdate(next, s + before.length, s + before.length + selected.length)
}

// 在当前行首插入前缀
function insertLine(prefix: string) {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, value } = ta
  const lineStart = value.lastIndexOf(NL, s - 1) + 1
  const next = value.slice(0, lineStart) + prefix + value.slice(lineStart)
  emitAndUpdate(next, s + prefix.length, s + prefix.length)
}

function insertHeading() { insertLine('### ') }
function wrapBold() { wrap('**', t('markdownEditor.scriptPlaceholders.bold')) }
function wrapItalic() { wrap('*', t('markdownEditor.scriptPlaceholders.italic')) }
function wrapStrike() { wrap('~~', t('markdownEditor.scriptPlaceholders.strike')) }
function wrapInlineCode() { wrap('`', 'code') }
function insertList(ordered: boolean) { insertLine(ordered ? '1. ' : '- ') }
function insertQuote() { insertLine('> ') }

function wrapCodeBlock() {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, selectionEnd: e, value } = ta
  const selected = value.slice(s, e) || t('markdownEditor.scriptPlaceholders.code')
  const block = FENCE + 'python' + NL + selected + NL + FENCE + NL
  const next = value.slice(0, s) + block + value.slice(e)
  // 光标定位到语言名，便于改写
  emitAndUpdate(next, s + FENCE.length, s + FENCE.length + 'python'.length)
}

function insertLink() {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, selectionEnd: e, value } = ta
  const selected = value.slice(s, e) || t('markdownEditor.scriptPlaceholders.linkText')
  const block = '[' + selected + '](https://)'
  const next = value.slice(0, s) + block + value.slice(e)
  const urlStart = s + selected.length + 3 // 跳过 `](`
  emitAndUpdate(next, urlStart, urlStart + 'https://'.length)
}

function insertTable() {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, value } = ta
  const block = NL + '| 列1 | 列2 | 列3 |' + NL + '| --- | --- | --- |' + NL + '| a | b | c |' + NL
  const next = value.slice(0, s) + block + value.slice(s)
  emitAndUpdate(next, s + block.length, s + block.length)
}

function insertHr() {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, value } = ta
  const block = NL + '---' + NL + NL
  const next = value.slice(0, s) + block + value.slice(s)
  emitAndUpdate(next, s + block.length, s + block.length)
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.md-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: $bg-tertiary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  overflow: hidden;
}

.md-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  padding: 6px 8px;
  background: $bg-secondary;
  border-bottom: 1px solid $border-color;
}

.md-btn {
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: $radius-sm;
  color: $text-secondary;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: rgba(var(--vs-accent-rgb), 0.08);
    color: $accent;
    border-color: rgba(var(--vs-accent-rgb), 0.15);
  }
}

.md-sep {
  width: 1px;
  height: 18px;
  margin: 0 4px;
  background: $border-color;
}

.md-split {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 0;
}

.md-edit-pane,
.md-preview-pane {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.md-preview-pane {
  border-left: 1px solid $border-color;
  background: $bg-secondary;
}

.md-preview-label {
  padding: 6px 12px;
  font-size: $font-caption;
  color: $text-disabled;
  border-bottom: 1px solid $border-subtle;
  background: $bg-tertiary;
}

.md-preview-scroll {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-lg;
}

.md-textarea {
  flex: 1;
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  padding: $spacing-lg;
  background: $bg-tertiary;
  color: $text-primary;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;

  &::placeholder {
    color: $text-disabled;
  }
}
</style>