<template>
  <div class="markdown-body" v-html="html" />
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { renderMarkdown, extractHeadings, type MdHeading } from '@/utils/markdown'

const props = defineProps<{ content: string }>()
const emit = defineEmits<{ (e: 'headings', headings: MdHeading[]): void }>()

const html = computed(() => renderMarkdown(props.content))
const headings = computed(() => extractHeadings(props.content))

// 标题变化时上报，供父组件渲染 TOC
watch(headings, (h) => emit('headings', h), { immediate: true })
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.markdown-body {
  color: $text-primary;
  font-size: $font-body;
  line-height: 1.7;
  word-break: break-word;

  :deep() {
    // 标题
    h1, h2, h3, h4, h5, h6 {
      margin: 1.4em 0 0.6em;
      font-weight: 600;
      line-height: 1.3;
      color: $text-primary;
    }
    h1 { font-size: 1.6em; border-bottom: 1px solid $border-subtle; padding-bottom: 0.3em; }
    h2 { font-size: 1.35em; border-bottom: 1px solid $border-subtle; padding-bottom: 0.3em; }
    h3 { font-size: 1.15em; }
    h4 { font-size: 1em; }
    h5, h6 { font-size: 0.9em; color: $text-secondary; }

    p { margin: 0.6em 0; }

    // 链接
    a { color: $accent; text-decoration: none; }
    a:hover { text-decoration: underline; }

    // 强调
    strong { font-weight: 600; color: $text-primary; }
    em { font-style: italic; }
    del { color: $text-disabled; }

    // 列表
    ul, ol { margin: 0.6em 0; padding-left: 1.8em; }
    li { margin: 0.2em 0; }

    // 引用
    blockquote {
      margin: 0.8em 0;
      padding: 0.4em 1em;
      border-left: 3px solid $accent;
      background: rgba(var(--vs-accent-rgb), 0.05);
      color: $text-secondary;
    }
    blockquote p { margin: 0.3em 0; }

    // 行内代码
    code {
      font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
      font-size: 0.9em;
      padding: 0.15em 0.4em;
      margin: 0 0.1em;
      background: $bg-tertiary;
      border: 1px solid $border-subtle;
      border-radius: $radius-sm;
      color: $text-primary;
    }

    // 代码块
    pre {
      margin: 0.8em 0;
      padding: $spacing-lg;
      background: $bg-tertiary;
      border: 1px solid $border-color;
      border-radius: $radius-md;
      overflow-x: auto;
    }
    pre code {
      display: block;
      padding: 0;
      margin: 0;
      background: transparent;
      border: none;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre;
    }

    // 表格
    table {
      margin: 0.8em 0;
      border-collapse: collapse;
      width: 100%;
      font-size: 0.95em;
    }
    th, td {
      border: 1px solid $border-color;
      padding: 0.4em 0.7em;
      text-align: left;
    }
    th {
      background: $bg-tertiary;
      font-weight: 600;
    }

    hr {
      border: none;
      border-top: 1px solid $border-color;
      margin: 1.2em 0;
    }

    img {
      max-width: 100%;
      border-radius: $radius-sm;
    }

    // highlight.js 仅做轻量着色（与暗色主题适配）
    .hljs-keyword,
    .hljs-selector-tag,
    .hljs-built_in,
    .hljs-name,
    .hljs-tag { color: $accent; }
    .hljs-string,
    .hljs-attr,
    .hljs-template-variable,
    .hljs-variable { color: $active; }
    .hljs-number,
    .hljs-literal { color: $medium; }
    .hljs-comment,
    .hljs-quote { color: $text-disabled; font-style: italic; }
    .hljs-title,
    .hljs-section,
    .hljs-function .hljs-title { color: $text-primary; font-weight: 600; }
    .hljs-type,
    .hljs-class .hljs-title { color: $high; }
  }
}
</style>
