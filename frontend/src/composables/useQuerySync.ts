import { ref, watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * 列表页筛选 / 分页状态 ↔ URL query 双向同步。
 *
 * 用法：
 * ```ts
 * const page = ref(1), pageSize = ref(20), q = ref('')
 *
 * useQuerySync(
 *   { page: { type: 'number' }, pageSize: { type: 'number' }, q: { type: 'string' } },
 *   { page, pageSize, q },
 *   loadData,
 * )
 * ```
 *
 * 行为与职责划分：
 * - **初始化**：`init()` 在 setup 中调用，以 URL 为准恢复状态（刷新页面保留筛选/分页）。
 * - **状态变化 → 仅写 URL**：防抖后 `router.replace` 写回（不产生历史记录），**不**触发加载；
 *   数据加载仍由页面自身的显式事件（search / reset / 分页 change 等）驱动，避免双发请求。
 * - **外部导航 → 重载**：浏览器前进/后退或手动改 URL 时，重读 query → 状态 → 触发 `onChange`。
 * - 数组以逗号连接序列化（如 `?severity=high,critical&tagIds=1,2`），与后端多值参数格式一致。
 * - 通过签名比对避免「写 URL ↔ 监听 URL」循环。
 */

export interface QueryFieldDef {
  type: 'string' | 'number' | 'string[]' | 'number[]'
  /** 该字段缺省时的兜底值（如数字类型默认 1）。 */
  default?: string | number | unknown[]
}

export type QueryState = Record<string, Ref<unknown>>

function defaultFor(def: QueryFieldDef): unknown {
  if ('default' in def) return def.default
  switch (def.type) {
    case 'number': return 1
    case 'string[]': return [] as string[]
    case 'number[]': return [] as number[]
    default: return ''
  }
}

/** 将状态值编码为 URL 中的字符串（数组逗号连接，空值 → undefined）。 */
function encodeValue(v: unknown): string | undefined {
  if (v === null || v === undefined) return undefined
  if (Array.isArray(v)) return v.length ? v.map(String).join(',') : undefined
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : undefined
  const s = String(v)
  return s === '' ? undefined : s
}

/** 将 URL 参数解码为状态值（兼容 string / string[] 两种形态）。 */
function decodeValue(raw: unknown, def: QueryFieldDef): unknown {
  if (raw === undefined || raw === null || raw === '') return defaultFor(def)
  const text = Array.isArray(raw) ? raw.join(',') : String(raw)
  switch (def.type) {
    case 'string':
      return text
    case 'number': {
      const n = Number(text)
      return Number.isFinite(n) ? n : defaultFor(def)
    }
    case 'string[]':
      return text.split(',').map((s) => s.trim()).filter(Boolean)
    case 'number[]':
      return text.split(',').map((s) => Number(s.trim())).filter((n) => Number.isFinite(n))
  }
}

/** 从准备好的查询对象生成可比较签名（键排序 + 规范化值）。 */
function canonicalSig(query: Record<string, unknown>): string {
  const parts: string[] = []
  for (const key of Object.keys(query).sort()) {
    const raw = query[key]
    if (raw === undefined || raw === null || raw === '') continue
    const text = Array.isArray(raw) ? raw.join(',') : String(raw)
    if (text) parts.push(`${key}=${text}`)
  }
  return parts.join('&')
}

export function useQuerySync(
  fields: Record<string, QueryFieldDef>,
  state: QueryState,
  onChange: () => void,
  debounceMs = 300,
) {
  const route = useRoute()
  const router = useRouter()

  /** 当前状态编码成的 query（仅包含非默认值字段）。 */
  function queryFromState(): Record<string, string> {
    const out: Record<string, string> = {}
    for (const key of Object.keys(fields)) {
      const encoded = encodeValue(state[key].value)
      if (encoded !== undefined) out[key] = encoded
    }
    return out
  }

  /** 从 route.query 读取并写回状态。 */
  function readFromRoute() {
    for (const key of Object.keys(fields)) {
      state[key].value = decodeValue(route.query[key], fields[key])
    }
  }

  let lastSig = ''
  let initialized = false
  let timer: ReturnType<typeof setTimeout> | null = null

  /**
   * 是否正从 URL 反向恢复状态。
   * 页面自身的 filter watch 在恢复期间应跳过（避免把 URL 页码等覆盖回默认值后再加载）。
   * 由于 Vue watch 回调默认非同步触发，同步置 false 即可覆盖「读→watch 调度→执行」的全过程。
   */
  const syncing = ref(false)

  /** 初始化（首次挂载时调用）：以 URL 为准恢复状态并记录签名。 */
  function init() {
    syncing.value = true
    readFromRoute()
    lastSig = canonicalSig(queryFromState())
    syncing.value = false
    initialized = true
  }

  // 状态变化 → 仅防抖写回 URL（不触发加载，加载由页面事件负责）
  watch(
    Object.values(state),
    () => {
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        const next = queryFromState()
        const sig = canonicalSig(next)
        if (sig === lastSig) return
        lastSig = sig
        router.replace({ query: next }).catch(() => {})
      }, debounceMs)
    },
    { deep: true },
  )

  // 外部导航（前进/后退、手动改 URL）→ 重读状态 + 重新加载
  watch(
    () => route.query,
    (q) => {
      if (!initialized) return // init() 之前（首帧）跳过
      const sig = canonicalSig({ ...q })
      const stateSig = canonicalSig(queryFromState())
      if (sig === stateSig) return // 由本组件写回触发的同值更新
      syncing.value = true
      readFromRoute()
      lastSig = canonicalSig(queryFromState())
      syncing.value = false
      onChange()
    },
  )

  return { init, syncing }
}

/** 便捷构造：把 reactive 对象字段转为 refs（toRef 的简化版）。
 *  实际使用直接 toRef 即可，此导出仅为统一入口。 */
export { toRef as toQueryRef } from 'vue'