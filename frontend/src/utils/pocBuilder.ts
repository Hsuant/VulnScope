/**
 * POC 表单构建器核心逻辑。
 *
 * 把结构化的「协议 + 请求 + 匹配器」状态生成/解析为 POC 内容文本，
 * 支持 nuclei 与 json 两种声明式格式；pocsuite3/raw-script 为代码，
 * 不参与结构化构建，仅走源码模式。
 *
 * 生成使用 js-yaml（nuclei）保证输出合法；解析同样走 js-yaml.load，
 * 保证编辑回填的可靠性。构建器状态会随 extra_meta.builder 持久化，
 * 保证编辑时精确回填。
 *
 * 字段命名与生成结构严格对齐 Nuclei 官方模板规范：
 *   https://docs.projectdiscovery.io/templates/reference
 */

import { dump, load } from 'js-yaml'
import type { AffectedVersion, PocCreatePayload, PocUpdatePayload, Reference } from '@/types/poc'

// ── 协议与字段结构 ───────────────────────────────────────────────

export type Protocol = 'http' | 'tcp' | 'dns' | 'network' | 'websocket'

export interface KeyValue {
  key: string
  value: string
}

// 模糊测试 payload 组（官方 payloads 字段：name -> value 列表）
export interface PayloadGroup {
  name: string
  values: string[]
}

export interface HttpSpec {
  method: string
  paths: string[]
  headers: KeyValue[]
  body: string
  // 重定向控制（官方字段 redirects / max-redirects）
  redirects: boolean
  maxRedirects: number
  // 请求模式（官方 path/raw 两种 HTTP 模式）
  mode: 'path' | 'raw'
  // raw 模式完整 HTTP 报文（支持多请求链）
  raw: string[]
  unsafe: boolean
  cookieReuse: boolean
  // 多请求链响应引用（官方 req-condition 字段）
  reqCondition: boolean
  // 模糊测试（官方 attack / payloads 字段）
  attack: 'none' | 'batteringram' | 'pitchfork' | 'clusterbomb'
  payloads: PayloadGroup[]
}

export interface TcpSpec {
  inputs: string[]
  port: string
  data: string
  readBytes: number
}

export interface DnsSpec {
  domains: string[]
  recursion: boolean
  queryType: string
  kclass: string
}

/** Network 协议多阶段输入（官方 inputs[] 的每一项）。 */
export interface NetworkStage {
  data: string
  read: number
}

export interface NetworkSpec {
  /** 目标主机列表（官方 host 字段） */
  host: string[]
  port: string
  /** 简单模式：单阶段发送数据 */
  data: string
  /** 简单模式：发送后读取字节数 */
  readBytes: number
  /** 高级模式：多阶段交互（非空时优先于 data/readBytes） */
  stages: NetworkStage[]
  /** TLS 加密（官方 item 级 tls 字段） */
  tls: boolean
  /** TLS SNI（官方 item 级 sni 字段） */
  tlsSni: string
}

export interface WebSocketSpec {
  /** 目标地址（官方 address 字段，非 url） */
  address: string
  /** 发送消息体（官方 input.data 字段） */
  inputData: string
  /** 每次读取字节数（官方 read-size 字段） */
  readSize: number
}

export interface Matcher {
  id: string
  type: 'word' | 'status' | 'dsl' | 'regex' | 'size' | 'binary' | 'condition'
  part: 'header' | 'body' | 'all' | 'error' | 'data' | 'response' | 'raw' | 'request' | ''
  words: string[]
  status: number[]
  condition: 'and' | 'or'
  negative: boolean
  // size 匹配器
  lt: number | null
  gt: number | null
  // binary 匹配器（十六进制串数组）
  binary: string[]
  // condition 匹配器：DSL 条件表达式（type: condition 时的官方 condition 字段）
  conditionExpression: string
}

export interface Extractor {
  id: string
  type: 'regex' | 'dsl' | 'json' | 'kval' | 'xpath'
  name: string
  part: '' | 'header' | 'body' | 'all'
  expressions: string[]
  group: number
  internal: boolean
  /** xpath 提取属性（官方 attribute 字段） */
  attribute: string
}

export interface BuilderState {
  protocol: Protocol
  /** 多个 matcher 条目之间的逻辑关系（官方 matchers-condition 字段） */
  matchersCondition: 'and' | 'or'
  http: HttpSpec
  tcp: TcpSpec
  dns: DnsSpec
  network: NetworkSpec
  websocket: WebSocketSpec
  matchers: Matcher[]
  extractors: Extractor[]
}

export const PROTOCOL_OPTIONS: { value: Protocol; label: string; desc: string }[] = [
  { value: 'http', label: 'HTTP', desc: 'Web 漏洞：方法 / 路径 / 请求头 / 请求体' },
  { value: 'tcp', label: 'TCP', desc: '网络服务：主机 / 端口 / 数据 / 读取' },
  { value: 'dns', label: 'DNS', desc: '域名解析：域名 / 记录类型 / 递归' },
  { value: 'network', label: 'Network', desc: '原始 TCP：TLS 加密 / 数据收发 / 字节读取' },
  { value: 'websocket', label: 'WebSocket', desc: 'WebSocket：地址 / 消息 / 字节读取' },
]

export const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH']
export const DNS_QUERY_TYPES = ['A', 'AAAA', 'NS', 'CNAME', 'TXT', 'MX', 'SOA', 'PTR', 'CAA']
// 官方支持的全部匹配器类型
export const MATCHER_TYPES = ['word', 'status', 'dsl', 'regex', 'size', 'binary', 'condition']
// 各协议合法的 matcher part 取值（官方规范）
export const MATCHER_PARTS = ['all', 'body', 'header']                 // http / tcp
export const MATCHER_PARTS_DNS = ['all', 'error', 'response', 'raw']   // dns
export const MATCHER_PARTS_NETWORK = ['all', 'data', 'request']        // network
export const MATCHER_PARTS_WS = ['all', 'data', 'message']             // websocket
export const EXTRACTOR_TYPES = ['regex', 'dsl', 'json', 'kval', 'xpath']
export const EXTRACTOR_PARTS = ['all', 'body', 'header']

/** 按协议返回合法的 matcher part 可选项。 */
export function getMatcherPartsForProtocol(protocol: Protocol): string[] {
  switch (protocol) {
    case 'dns':
      return MATCHER_PARTS_DNS
    case 'network':
      return MATCHER_PARTS_NETWORK
    case 'websocket':
      return MATCHER_PARTS_WS
    default:
      return MATCHER_PARTS
  }
}

let _matcherSeq = 0
export function genMatcherId(): string {
  _matcherSeq += 1
  // 用递增序号 + 计数器构造稳定唯一 id（不依赖 Math.random/Date）
  return `m${_matcherSeq}`
}

export function createEmptyState(): BuilderState {
  return {
    protocol: 'http',
    matchersCondition: 'and',
    http: {
      method: 'GET',
      paths: ['{{BaseURL}}'],
      headers: [],
      body: '',
      redirects: false,
      maxRedirects: 3,
      mode: 'path',
      raw: [''],
      unsafe: false,
      cookieReuse: false,
      reqCondition: false,
      attack: 'none',
      payloads: [],
    },
    tcp: { inputs: ['{{Hostname}}'], port: '', data: '', readBytes: 0 },
    dns: { domains: ['{{Hostname}}'], recursion: false, queryType: 'A', kclass: 'inet' },
    network: { host: ['{{Hostname}}'], port: '', data: '', readBytes: 0, stages: [], tls: false, tlsSni: '' },
    websocket: { address: '', inputData: '', readSize: 4096 },
    matchers: [
      { id: genMatcherId(), type: 'word', part: 'body', words: ['vulnerable'], status: [], condition: 'or', negative: false, lt: null, gt: null, binary: [], conditionExpression: '' },
    ],
    extractors: [],
  }
}

// ── 生成器 ───────────────────────────────────────────────────────

export interface BuildContext {
  name: string
  title?: string
  author?: string
  severity: string
  description?: string
  cveIds: string[]
  tagNames: string[]
  format: string
  language?: string
  source?: string
  references?: Reference[]
  fofaSyntax?: string
  shodanSyntax?: string
  affectedVersions?: AffectedVersion[]
  state: BuilderState
}

// ── 元数据拼装：把参考链接 / FOFA / Shodan / 受影响版本 / 来源 / 格式汇入 info ──

function buildReferenceList(references?: Reference[]): string[] | undefined {
  if (!references?.length) return undefined
  const urls = references.map((r) => r.url).filter((u) => u.trim() !== '')
  return urls.length ? urls : undefined
}

function buildAffectedList(versions?: AffectedVersion[]): string[] | undefined {
  if (!versions?.length) return undefined
  const items = versions.map((v) => {
    const parts: string[] = []
    if (v.version_start) parts.push(`${v.version_start_type} ${v.version_start}`)
    if (v.version_end) parts.push(`${v.version_end_type} ${v.version_end}`)
    return parts.join(' ~ ')
  }).filter((s) => s.trim() !== '')
  return items.length ? items : undefined
}

function buildMetadata(ctx: BuildContext): Record<string, unknown> | undefined {
  const meta: Record<string, unknown> = {}
  if (ctx.fofaSyntax) meta['fofa-query'] = ctx.fofaSyntax
  if (ctx.shodanSyntax) meta['shodan-query'] = ctx.shodanSyntax
  if (ctx.source) meta.source = ctx.source
  if (ctx.format) meta.format = ctx.format
  const affected = buildAffectedList(ctx.affectedVersions)
  if (affected) meta.affected = affected
  return Object.keys(meta).length ? meta : undefined
}

function buildMatchers(matchers: Matcher[]): Record<string, unknown>[] {
  return matchers.map((m) => {
    const o: Record<string, unknown> = { type: m.type }
    if (m.type !== 'status' && m.part) o.part = m.part
    if (m.type === 'word') {
      o.words = m.words.filter((w) => w !== '')
      o.condition = m.condition
    }
    // 关键修复：regex 类型必须输出 regex 键（原实现错误输出 words，导致正则失效）
    if (m.type === 'regex') {
      o.regex = m.words.filter((w) => w !== '')
      o.condition = m.condition
    }
    if (m.type === 'status') {
      const codes = m.status.filter((n) => !Number.isNaN(n))
      if (codes.length) o.status = codes // 空状态码数组跳过，避免输出 status: []
    }
    if (m.type === 'dsl') {
      o.dsl = m.words.filter((w) => w !== '')
      o.condition = m.condition
    }
    if (m.type === 'size') {
      if (m.lt !== null && m.lt !== undefined && !Number.isNaN(m.lt)) o.lt = m.lt
      if (m.gt !== null && m.gt !== undefined && !Number.isNaN(m.gt)) o.gt = m.gt
    }
    if (m.type === 'binary') {
      o.binary = m.binary.filter((b) => b.trim() !== '')
    }
    // condition 匹配器：输出官方 condition 表达式字符串（非 and/or）
    if (m.type === 'condition') {
      o.condition = m.conditionExpression.trim()
    }
    if (m.negative) o.negative = true
    return o
  })
}

function buildExtractors(extractors: Extractor[]): Record<string, unknown>[] {
  return extractors.map((e) => {
    const o: Record<string, unknown> = { type: e.type }
    if (e.name) o.name = e.name
    const exprs = e.expressions.filter((x) => x !== '')
    if (exprs.length) o[e.type] = exprs
    if (e.type === 'regex' && e.group) o.group = e.group
    if (e.part) o.part = e.part
    if (e.internal) o.internal = true
    // xpath 属性提取（官方 attribute 字段）
    if (e.type === 'xpath' && e.attribute.trim()) o.attribute = e.attribute.trim()
    return o
  })
}

/** 生成各协议请求条目。matchers-condition 置于请求条目层级（官方规范）。 */
function buildProtocolItem(
  s: BuilderState,
  matchers: Record<string, unknown>[],
  extractors: Record<string, unknown>[],
): Record<string, unknown> {
  const item: Record<string, unknown> = {}

  if (s.protocol === 'http') {
    if (s.http.mode === 'raw') {
      // raw 模式：完整 HTTP 报文，支持多请求链（raw 数组）
      const raws = s.http.raw.filter((r) => r.trim() !== '')
      if (raws.length) item.raw = raws
      if (s.http.unsafe) item.unsafe = true
      if (s.http.cookieReuse) item['cookie-reuse'] = true
    } else {
      item.method = s.http.method
      item.path = s.http.paths.filter((p) => p !== '')
      const headers = s.http.headers.filter((kv) => kv.key.trim() !== '')
      if (headers.length) {
        item.headers = Object.fromEntries(headers.map((kv) => [kv.key, kv.value]))
      }
      if (s.http.body.trim()) item.body = s.http.body
      if (s.http.redirects) {
        item.redirects = true
        item['max-redirects'] = s.http.maxRedirects
      }
    }
    // 多请求链响应引用
    if (s.http.reqCondition) item['req-condition'] = true
    // 模糊测试（attack + payloads）
    if (s.http.attack !== 'none') {
      item.attack = s.http.attack
      const payloadObj: Record<string, unknown> = {}
      for (const pg of s.http.payloads) {
        const values = pg.values.filter((v) => v.trim() !== '')
        if (pg.name.trim() && values.length) payloadObj[pg.name.trim()] = values
      }
      if (Object.keys(payloadObj).length) item.payloads = payloadObj
    }
  } else if (s.protocol === 'tcp') {
    item.inputs = s.tcp.inputs.filter((i) => i !== '')
    if (s.tcp.port.trim()) item.port = s.tcp.port
    if (s.tcp.data.trim()) item.data = s.tcp.data
    if (s.tcp.readBytes > 0) item['read-size'] = `${s.tcp.readBytes}b`
  } else if (s.protocol === 'network') {
    // 官方 network 结构：inputs[]（多阶段对象）+ host + item 级 tls/sni
    if (s.network.stages.length > 0) {
      item.inputs = s.network.stages.map((st) => {
        const input: Record<string, unknown> = { data: st.data }
        if (st.read > 0) input.read = st.read
        return input
      })
    } else if (s.network.data.trim() || s.network.readBytes > 0) {
      const input: Record<string, unknown> = {}
      if (s.network.data.trim()) input.data = s.network.data
      if (s.network.readBytes > 0) input.read = s.network.readBytes
      item.inputs = [input]
    }
    item.host = s.network.host.filter((h) => h !== '')
    if (s.network.port.trim()) item.port = s.network.port
    // 关键修复：tls/sni 必须位于请求条目层级，而非嵌套 network.xxx
    if (s.network.tls) item.tls = true
    if (s.network.tlsSni.trim()) item.sni = s.network.tlsSni
  } else if (s.protocol === 'websocket') {
    // 官方 websocket 结构：address + input.data + read-size（无 url/method/body）
    if (s.websocket.address.trim()) item.address = s.websocket.address
    if (s.websocket.inputData.trim()) {
      item.input = { data: s.websocket.inputData }
    }
    if (s.websocket.readSize > 0) item['read-size'] = s.websocket.readSize
  } else {
    // dns
    item.name = '{{FQDN}}'
    const domains = s.dns.domains.filter((d) => d !== '')
    if (domains.length) item.domains = domains
    if (s.dns.queryType) item.type = s.dns.queryType
    if (s.dns.recursion) item.recursion = true
    if (s.dns.kclass) item.class = s.dns.kclass
  }

  // 多个 matcher 时输出官方 matchers-condition（控制条目间逻辑）
  if (matchers.length > 1) item['matchers-condition'] = s.matchersCondition
  item.matchers = matchers
  if (extractors.length) item.extractors = extractors
  return item
}

function buildNucleiObject(ctx: BuildContext): Record<string, unknown> {
  const s = ctx.state
  const tags = [
    ...ctx.tagNames.map((t) => t.toLowerCase().replace(/[^a-z0-9-]/g, '-')),
    ...ctx.cveIds.map((c) => c.toLowerCase()),
  ].filter(Boolean)

  const info: Record<string, unknown> = {
    name: ctx.title || ctx.name,
    author: ctx.author || 'unknown',
    severity: ctx.severity,
  }
  if (ctx.description) info.description = ctx.description
  if (ctx.cveIds.length) {
    info.classification = { 'cve-id': ctx.cveIds }
  }
  if (tags.length) info.tags = tags.join(', ')

  const reference = buildReferenceList(ctx.references)
  if (reference) info.reference = reference
  const metadata = buildMetadata(ctx)
  if (metadata) info.metadata = metadata

  const obj: Record<string, unknown> = { id: ctx.name, info }
  const matchers = buildMatchers(s.matchers)
  const extractors = buildExtractors(s.extractors)
  const item = buildProtocolItem(s, matchers, extractors)

  obj[s.protocol] = [item]
  return obj
}

export function generateNucleiYaml(ctx: BuildContext): string {
  const obj = buildNucleiObject(ctx)
  return dump(obj, { lineWidth: -1, noRefs: true })
}

export function generateJson(ctx: BuildContext): string {
  const s = ctx.state
  const obj: Record<string, unknown> = {
    name: ctx.name,
    title: ctx.title || ctx.name,
    author: ctx.author || 'unknown',
    severity: ctx.severity,
    description: ctx.description || '',
    vulnerabilities: ctx.cveIds,
    tags: ctx.tagNames,
    matchers: buildMatchers(s.matchers),
    matchersCondition: s.matchersCondition,
  }
  const reference = buildReferenceList(ctx.references)
  if (reference) obj.references = reference
  const metadata = buildMetadata(ctx)
  if (metadata) obj.metadata = metadata
  const extractors = buildExtractors(s.extractors)
  if (extractors.length) obj.extractors = extractors
  if (s.protocol === 'http') {
    const request: Record<string, unknown> = s.http.mode === 'raw'
      ? {
          raw: s.http.raw.filter((r) => r.trim() !== ''),
          ...(s.http.unsafe ? { unsafe: true } : {}),
          ...(s.http.cookieReuse ? { cookieReuse: true } : {}),
        }
      : {
          method: s.http.method,
          path: s.http.paths.filter((p) => p !== ''),
          headers: Object.fromEntries(s.http.headers.filter((kv) => kv.key.trim() !== '').map((kv) => [kv.key, kv.value])),
          ...(s.http.body.trim() ? { body: s.http.body } : {}),
          ...(s.http.redirects ? { redirects: true, maxRedirects: s.http.maxRedirects } : {}),
        }
    if (s.http.reqCondition) request.reqCondition = true
    if (s.http.attack !== 'none') {
      request.attack = s.http.attack
      const payloadObj: Record<string, string[]> = {}
      for (const pg of s.http.payloads) {
        const values = pg.values.filter((v) => v.trim() !== '')
        if (pg.name.trim() && values.length) payloadObj[pg.name.trim()] = values
      }
      if (Object.keys(payloadObj).length) request.payloads = payloadObj
    }
    obj.request = request
  } else if (s.protocol === 'tcp') {
    obj.request = {
      protocol: 'tcp',
      host: s.tcp.inputs.filter((i) => i !== ''),
      ...(s.tcp.port.trim() ? { port: s.tcp.port } : {}),
      ...(s.tcp.data.trim() ? { data: s.tcp.data } : {}),
      ...(s.tcp.readBytes > 0 ? { readSize: s.tcp.readBytes } : {}),
    }
  } else if (s.protocol === 'network') {
    obj.request = {
      protocol: 'network',
      host: s.network.host.filter((i) => i !== ''),
      ...(s.network.port.trim() ? { port: s.network.port } : {}),
      ...(s.network.data.trim() ? { data: s.network.data } : {}),
      ...(s.network.readBytes > 0 ? { readSize: s.network.readBytes } : {}),
      stages: s.network.stages,
      tls: s.network.tls,
      ...(s.network.tlsSni.trim() ? { sni: s.network.tlsSni } : {}),
    }
  } else if (s.protocol === 'websocket') {
    obj.request = {
      protocol: 'websocket',
      ...(s.websocket.address.trim() ? { address: s.websocket.address } : {}),
      ...(s.websocket.inputData.trim() ? { input: { data: s.websocket.inputData } } : {}),
      readSize: s.websocket.readSize,
    }
  } else {
    // dns
    obj.request = {
      protocol: 'dns',
      domain: s.dns.domains.filter((d) => d !== ''),
      type: s.dns.queryType,
      class: s.dns.kclass,
      recursion: s.dns.recursion,
    }
  }
  return JSON.stringify(obj, null, 2)
}

export function generateContent(ctx: BuildContext): string {
  if (ctx.format === 'json') return generateJson(ctx)
  return generateNucleiYaml(ctx)
}

// ── 解析器（content → state）──────────────────────────────────────

function toMatchers(arr: unknown): Matcher[] {
  if (!Array.isArray(arr)) return []
  return arr.map((m: Record<string, unknown>) => {
    const type = (m.type as Matcher['type']) || 'word'
    return {
      id: genMatcherId(),
      type,
      part: (m.part as Matcher['part']) || '',
      // 关键修复：解析 regex 类型的 regex 键（原实现丢失 m.regex）
      words: Array.isArray(m.words) ? m.words.map(String)
        : Array.isArray(m.regex) ? m.regex.map(String)
        : Array.isArray(m.dsl) ? m.dsl.map(String)
        : Array.isArray(m.binary) ? m.binary.map(String) : [],
      status: Array.isArray(m.status) ? m.status.map((n) => Number(n)).filter((n) => !Number.isNaN(n)) : [],
      condition: (m.condition as Matcher['condition']) || 'or',
      negative: !!m.negative,
      lt: m.lt !== undefined && m.lt !== null ? Number(m.lt) : null,
      gt: m.gt !== undefined && m.gt !== null ? Number(m.gt) : null,
      binary: Array.isArray(m.binary) ? m.binary.map(String) : [],
      // condition 匹配器：m.condition 若是非 and/or 的字符串即视为表达式
      conditionExpression: typeof m.condition === 'string' && m.condition !== 'and' && m.condition !== 'or'
        ? (m.condition as string) : '',
    }
  })
}

function toExtractors(arr: unknown): Extractor[] {
  if (!Array.isArray(arr)) return []
  return arr.map((e: Record<string, unknown>) => {
    const type = (e.type as Extractor['type']) || 'regex'
    const exprs = Array.isArray(e[type]) ? (e[type] as unknown[]).map(String) : []
    return {
      id: genMatcherId(),
      type,
      name: String(e.name ?? ''),
      part: (e.part as Extractor['part']) || '',
      expressions: exprs,
      group: Number(e.group ?? 0) || 0,
      internal: !!e.internal,
      attribute: String(e.attribute ?? ''),
    }
  })
}

function applyRequestItem(state: BuilderState, item: Record<string, unknown>): void {
  // 解析请求级 matchers-condition
  state.matchersCondition = item['matchers-condition'] === 'or' ? 'or' : 'and'
  state.matchers = toMatchers(item.matchers)
  state.extractors = toExtractors(item.extractors)
}

export function parseNucleiYaml(content: string): BuilderState {
  const state = createEmptyState()
  let obj: Record<string, unknown>
  try {
    obj = load(content) as Record<string, unknown>
  } catch {
    return state
  }
  if (!obj || typeof obj !== 'object') return state

  if (Array.isArray(obj.http) && obj.http.length) {
    state.protocol = 'http'
    const item = obj.http[0] as Record<string, unknown>
    if (Array.isArray(item.raw) && item.raw.length) {
      state.http.mode = 'raw'
      state.http.raw = item.raw.map(String)
      state.http.unsafe = !!item.unsafe
      state.http.cookieReuse = !!item['cookie-reuse']
    } else {
      state.http.method = String(item.method ?? 'GET')
      state.http.paths = Array.isArray(item.path) ? item.path.map(String) : (item.path ? [String(item.path)] : ['{{BaseURL}}'])
      state.http.headers = item.headers && typeof item.headers === 'object'
        ? Object.entries(item.headers).map(([k, v]) => ({ key: k, value: String(v) }))
        : []
      state.http.body = String(item.body ?? '')
      state.http.redirects = !!item.redirects
      state.http.maxRedirects = Number(item['max-redirects'] ?? 3) || 3
    }
    state.http.reqCondition = !!item['req-condition']
    state.http.attack = ['none', 'batteringram', 'pitchfork', 'clusterbomb'].includes(String(item.attack))
      ? (String(item.attack) as HttpSpec['attack'])
      : 'none'
    if (item.payloads && typeof item.payloads === 'object') {
      state.http.payloads = Object.entries(item.payloads).map(([name, values]) => ({
        name,
        values: Array.isArray(values) ? values.map(String) : [String(values)],
      }))
    }
    applyRequestItem(state, item)
  } else if (Array.isArray(obj.tcp) && obj.tcp.length) {
    state.protocol = 'tcp'
    const item = obj.tcp[0] as Record<string, unknown>
    state.tcp.inputs = Array.isArray(item.inputs) ? item.inputs.map(String) : (item.host ? [String(item.host)] : ['{{Hostname}}'])
    state.tcp.port = String(item.port ?? '')
    state.tcp.data = String(item.data ?? '')
    const rs = String(item['read-size'] ?? '').replace(/b$/i, '')
    state.tcp.readBytes = parseInt(rs, 10) || 0
    applyRequestItem(state, item)
  } else if (Array.isArray(obj.network) && obj.network.length) {
    state.protocol = 'network'
    const item = obj.network[0] as Record<string, unknown>
    // 主机：官方为 host 字段；兼容旧格式将字符串 input 视为主机名
    state.network.host = Array.isArray(item.host) ? item.host.map(String)
      : (item.host ? [String(item.host)]
      : (Array.isArray(item.inputs) && item.inputs.length && typeof item.inputs[0] === 'string'
        ? item.inputs.map(String) : ['{{Hostname}}']))
    state.network.port = String(item.port ?? '')
    // 多阶段 inputs（对象数组）
    if (Array.isArray(item.inputs) && item.inputs.length && typeof item.inputs[0] === 'object' && item.inputs[0] !== null) {
      state.network.stages = (item.inputs as Record<string, unknown>[]).map((input) => ({
        data: String(input.data ?? ''),
        read: Number(input.read ?? 0),
      }))
      state.network.data = state.network.stages.length ? state.network.stages[0].data : ''
      state.network.readBytes = state.network.stages.length ? state.network.stages[0].read : 0
    } else {
      state.network.data = String(item.data ?? '')
      const rs = String(item['read-size'] ?? '').replace(/b$/i, '')
      state.network.readBytes = parseInt(rs, 10) || 0
    }
    // 关键修复：tls/sni 从请求条目层级解析（原实现嵌套在 item.network）
    state.network.tls = !!item.tls
    state.network.tlsSni = String(item.sni ?? '')
    applyRequestItem(state, item)
  } else if (Array.isArray(obj.websocket) && obj.websocket.length) {
    state.protocol = 'websocket'
    const item = obj.websocket[0] as Record<string, unknown>
    // 关键修复：官方字段为 address + input.data + read-size
    state.websocket.address = String(item.address ?? '')
    const input = item.input as Record<string, unknown> | undefined
    state.websocket.inputData = String(input?.data ?? '')
    state.websocket.readSize = Number(item['read-size'] ?? 0) || 0
    applyRequestItem(state, item)
  } else if (Array.isArray(obj.dns) && obj.dns.length) {
    state.protocol = 'dns'
    const item = obj.dns[0] as Record<string, unknown>
    state.dns.domains = Array.isArray(item.domains) ? item.domains.map(String) : ['{{Hostname}}']
    state.dns.queryType = String(item.type ?? 'A')
    state.dns.recursion = !!item.recursion
    state.dns.kclass = String(item.class ?? 'inet')
    applyRequestItem(state, item)
  }
  if (!state.matchers.length) state.matchers = createEmptyState().matchers
  return state
}

export function parseJson(content: string): BuilderState {
  const state = createEmptyState()
  let obj: Record<string, any>
  try {
    obj = JSON.parse(content)
  } catch {
    return state
  }
  const req = obj.request || {}
  if (req.protocol === 'tcp') {
    state.protocol = 'tcp'
    state.tcp.inputs = Array.isArray(req.host) ? req.host : (req.host ? [req.host] : ['{{Hostname}}'])
    state.tcp.port = String(req.port ?? '')
    state.tcp.data = String(req.data ?? '')
    state.tcp.readBytes = Number(req.readSize ?? 0)
  } else if (req.protocol === 'network') {
    state.protocol = 'network'
    state.network.host = Array.isArray(req.host) ? req.host : (req.host ? [req.host] : ['{{Hostname}}'])
    state.network.port = String(req.port ?? '')
    state.network.data = String(req.data ?? '')
    state.network.readBytes = Number(req.readSize ?? 0)
    state.network.tls = !!req.tls
    state.network.tlsSni = String(req.sni ?? '')
    if (Array.isArray(req.stages)) {
      state.network.stages = req.stages.map((s: { data?: string; read?: number }) => ({
        data: String(s.data ?? ''),
        read: Number(s.read ?? 0),
      }))
    }
  } else if (req.protocol === 'websocket') {
    state.protocol = 'websocket'
    state.websocket.address = String(req.address ?? '')
    state.websocket.inputData = String(req.input?.data ?? '')
    state.websocket.readSize = Number(req.readSize ?? 0)
  } else if (req.protocol === 'dns') {
    state.protocol = 'dns'
    state.dns.domains = Array.isArray(req.domain) ? req.domain : (req.domain ? [req.domain] : ['{{Hostname}}'])
    state.dns.queryType = String(req.type ?? 'A')
    state.dns.recursion = !!req.recursion
    state.dns.kclass = String(req.class ?? 'inet')
  } else if (req.protocol === 'http' || req.raw || req.method || req.path) {
    state.protocol = 'http'
    if (Array.isArray(req.raw) && req.raw.length) {
      state.http.mode = 'raw'
      state.http.raw = req.raw.map(String)
      state.http.unsafe = !!req.unsafe
      state.http.cookieReuse = !!req.cookieReuse
    } else {
      state.http.method = String(req.method ?? 'GET')
      state.http.paths = Array.isArray(req.path) ? req.path : (req.path ? [req.path] : ['{{BaseURL}}'])
      state.http.headers = Object.entries(req.headers || {}).map(([k, v]) => ({ key: k, value: String(v) }))
      state.http.body = String(req.body ?? '')
      state.http.redirects = !!req.redirects
      state.http.maxRedirects = Number(req.maxRedirects ?? 3) || 3
    }
    state.http.reqCondition = !!req.reqCondition
    state.http.attack = ['none', 'batteringram', 'pitchfork', 'clusterbomb'].includes(String(req.attack))
      ? (String(req.attack) as HttpSpec['attack'])
      : 'none'
    if (req.payloads && typeof req.payloads === 'object') {
      state.http.payloads = Object.entries(req.payloads).map(([name, values]) => ({
        name,
        values: Array.isArray(values) ? values.map(String) : [String(values)],
      }))
    }
  }
  state.matchers = toMatchers(obj.matchers)
  state.extractors = toExtractors(obj.extractors)
  state.matchersCondition = obj.matchersCondition === 'or' ? 'or' : 'and'
  if (!state.matchers.length) state.matchers = createEmptyState().matchers
  return state
}

export function parseContent(content: string, format: string): BuilderState {
  if (format === 'json') return parseJson(content)
  return parseNucleiYaml(content)
}

export function canBuild(format: string): boolean {
  return format === 'nuclei' || format === 'json'
}

// ── 注入到 payload：把 builder state 持久化到 extra_meta ─────────

export function withBuilderMeta(
  payload: PocCreatePayload | PocUpdatePayload,
  state: BuilderState | null,
): PocCreatePayload | PocUpdatePayload {
  if (!state) return payload
  const extra = { ...(payload.extra_meta || {}), builder: state }
  return { ...payload, extra_meta: extra }
}

export function readBuilderMeta(extraMeta: Record<string, any> | null): BuilderState | null {
  const b = extraMeta?.builder
  if (b && typeof b === 'object' && b.protocol) return b as BuilderState
  return null
}

/** 兼容旧版 extra_meta.builder：把旧字段迁移到新结构（防止编辑旧 POC 时字段失效）。 */
export function migrateBuilderState(saved: Partial<BuilderState> | null | undefined): BuilderState {
  const state = createEmptyState()
  if (!saved || typeof saved !== 'object') return state
  if (saved.protocol) state.protocol = saved.protocol
  if (saved.matchersCondition) state.matchersCondition = saved.matchersCondition
  const oldHttp = saved.http as (Partial<HttpSpec> | undefined)
  if (oldHttp) {
    state.http.method = oldHttp.method ?? state.http.method
    state.http.paths = oldHttp.paths?.length ? oldHttp.paths : state.http.paths
    state.http.headers = oldHttp.headers ?? state.http.headers
    state.http.body = oldHttp.body ?? state.http.body
    state.http.redirects = oldHttp.redirects ?? state.http.redirects
    state.http.maxRedirects = oldHttp.maxRedirects ?? state.http.maxRedirects
    state.http.mode = oldHttp.mode ?? state.http.mode
    state.http.raw = oldHttp.raw?.length ? oldHttp.raw : state.http.raw
    state.http.unsafe = oldHttp.unsafe ?? state.http.unsafe
    state.http.cookieReuse = oldHttp.cookieReuse ?? state.http.cookieReuse
    state.http.reqCondition = oldHttp.reqCondition ?? state.http.reqCondition
    state.http.attack = oldHttp.attack ?? state.http.attack
    state.http.payloads = oldHttp.payloads ?? state.http.payloads
  }
  const oldNet = saved.network as (Partial<NetworkSpec> & { inputs?: string[] } | undefined)
  if (oldNet) {
    // 旧版 inputs 实为主机列表 → 迁移到 host
    const hosts = oldNet.host?.length ? oldNet.host : (oldNet.inputs?.length ? oldNet.inputs : state.network.host)
    state.network.host = hosts
    state.network.port = oldNet.port ?? state.network.port
    state.network.data = oldNet.data ?? state.network.data
    state.network.readBytes = oldNet.readBytes ?? state.network.readBytes
    state.network.stages = oldNet.stages?.length ? oldNet.stages : state.network.stages
    state.network.tls = oldNet.tls ?? state.network.tls
    state.network.tlsSni = oldNet.tlsSni ?? state.network.tlsSni
  }
  const oldWs = saved.websocket as (Partial<WebSocketSpec> & { url?: string; body?: string; readOnce?: boolean } | undefined)
  if (oldWs) {
    // 旧版 url/body/readOnce → 迁移到 address/inputData/readSize
    state.websocket.address = oldWs.address ?? oldWs.url ?? state.websocket.address
    state.websocket.inputData = oldWs.inputData ?? oldWs.body ?? state.websocket.inputData
    state.websocket.readSize = oldWs.readSize && oldWs.readSize > 0
      ? oldWs.readSize
      : (oldWs.readOnce ? 4096 : state.websocket.readSize)
  }
  if (saved.tcp) { state.tcp = { ...state.tcp, ...saved.tcp } }
  if (saved.dns) { state.dns = { ...state.dns, ...saved.dns } }
  if (Array.isArray(saved.matchers)) {
    // 兼容旧版 matcher 缺少新字段（conditionExpression 等），逐项补齐默认值
    state.matchers = saved.matchers.map((m: Matcher): Matcher => {
      const p = m as Partial<Matcher>
      return {
        ...p,
        id: p.id ?? genMatcherId(),
        type: p.type ?? 'word',
        part: p.part ?? '',
        words: p.words ?? [''],
        status: p.status ?? [],
        condition: p.condition ?? 'or',
        negative: p.negative ?? false,
        lt: p.lt ?? null,
        gt: p.gt ?? null,
        binary: p.binary ?? [],
        conditionExpression: p.conditionExpression ?? '',
      }
    })
  }
  if (Array.isArray(saved.extractors)) {
    state.extractors = saved.extractors.map((e: Extractor): Extractor => {
      const p = e as Partial<Extractor>
      return {
        ...p,
        id: p.id ?? genMatcherId(),
        type: p.type ?? 'regex',
        name: p.name ?? '',
        part: p.part ?? '',
        expressions: p.expressions ?? [''],
        group: p.group ?? 0,
        internal: p.internal ?? false,
        attribute: p.attribute ?? '',
      }
    })
  }
  if (!state.matchers.length) state.matchers = createEmptyState().matchers
  return state
}