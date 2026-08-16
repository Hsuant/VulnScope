/**
 * Markdown 渲染工具：markdown-it + highlight.js 代码高亮 + DOMPurify 消毒。
 *
 * 安全策略（这是漏洞管理平台，内容来源混杂：导入/AI/爬取都可能产出）：
 * - markdown-it 禁用原始 HTML 注入（html: false）
 * - 链接强制 target=_blank + rel=noopener noreferrer，仅放行 http/https/mailto
 * - DOMPurify 白名单兜底，禁用 script/style/iframe/form 等危险标签与事件属性
 * - 代码块超过 50KB 跳过高亮（防 ReDoS / 卡顿），按纯文本渲染
 *
 * 渲染产出的 HTML 已消毒，可直接 v-html。
 */

import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/common'
import DOMPurify from 'dompurify'

export interface MdHeading {
  level: number
  text: string
  slug: string
}

// 超大代码块长度，超过则跳过高亮
const MAX_HIGHLIGHT_LEN = 50_000

// 直接 new 推断实例类型（避免 export= 模块默认导入下的命名空间类型不可用）
const md = new MarkdownIt({
  html: false, // 禁用原始 HTML 注入
  breaks: true, // 单换行 → <br>
  linkify: true, // 自动识别裸链接
  highlight(str: string, lang: string): string {
    if (str.length > MAX_HIGHLIGHT_LEN) return '' // 超长跳过高亮
    const language = lang && hljs.getLanguage(lang) ? lang : ''
    if (language) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language }).value}</code></pre>`
      } catch {
        // fallthrough
      }
    }
    return '' // 返回空串让 markdown-it 自行转义输出 <pre><code>
  },
})

// 外链安全：给 <a> 注入 target=_blank + rel=noopener noreferrer
// 直接赋值到 renderer.rules，参数由 RenderRule 上下文推断类型
md.renderer.rules.link_open = function (tokens, idx, options, _env, self) {
  const token = tokens[idx]
  const targetIdx = token.attrIndex('target')
  if (targetIdx < 0) token.attrPush(['target', '_blank'])
  else if (token.attrs) token.attrs[targetIdx][1] = '_blank'
  const relIdx = token.attrIndex('rel')
  if (relIdx < 0) token.attrPush(['rel', 'noopener noreferrer'])
  else if (token.attrs) token.attrs[relIdx][1] = 'noopener noreferrer'
  return self.renderToken(tokens, idx, options)
}

// 标题注入 id，供 TOC 锚点跳转
md.renderer.rules.heading_open = function (tokens, idx, options, _env, self) {
  const token = tokens[idx]
  const next = tokens[idx + 1]
  const text = next && next.type === 'inline' ? next.content : ''
  token.attrPush(['id', slugify(text)])
  return self.renderToken(tokens, idx, options)
}

// ── DOMPurify 白名单 ───────────────────────────────────────────────

const SANITIZE_CONFIG = {
  ALLOWED_TAGS: [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'hr',
    'a', 'img',
    'ul', 'ol', 'li',
    'code', 'pre', 'blockquote',
    'strong', 'em', 'del', 's', 'sup', 'sub', 'mark',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'span', 'div',
  ],
  ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'target', 'rel', 'id'],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: ['style', 'script', 'iframe', 'form', 'input', 'button', 'object', 'embed', 'link', 'meta', 'base'],
  FORBID_ATTR: ['style', 'srcset', 'formaction'],
  // 仅放行 http/https/mailto（拦截 javascript:/data:/vbscript:）
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z0-9-]+?:)/i,
}

// ── 公开 API ──────────────────────────────────────────────────────

let _slugCounters: Record<string, number> = {}

/** 把标题文本转为锚点 slug，同一渲染批次内去重。 */
export function slugify(text: string): string {
  let s = text.trim().toLowerCase()
  s = s.replace(/[^\w一-龥\s-]/g, '').replace(/\s+/g, '-')
  s = s.replace(/-{2,}/g, '-').replace(/^-|-$/g, '')
  if (!s) s = 'section'
  if (_slugCounters[s] != null) {
    _slugCounters[s] += 1
    s = `${s}-${_slugCounters[s]}`
  } else {
    _slugCounters[s] = 0
  }
  return s
}

/** 渲染 Markdown 为消毒后的 HTML 字符串。 */
export function renderMarkdown(content: string): string {
  _slugCounters = {} // 每次渲染重置 slug 计数器，保证锚点唯一
  const dirty = md.render(content || '')
  // DOMPurify 在运行时返回 string，类型上为 TrustedHTML 品牌类型，转换回 string
  return DOMPurify.sanitize(dirty, SANITIZE_CONFIG) as unknown as string
}

/** 从 Markdown 源文本提取标题列表（用于 TOC）。 */
export function extractHeadings(content: string): MdHeading[] {
  _slugCounters = {}
  const tokens = md.parse(content || '', {})
  const headings: MdHeading[] = []
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i]
    if (t.type === 'heading_open') {
      const level = Number(t.tag.slice(1))
      const next = tokens[i + 1]
      const text = next && next.type === 'inline' ? next.content : ''
      headings.push({ level, text, slug: slugify(text) })
    }
  }
  return headings
}
