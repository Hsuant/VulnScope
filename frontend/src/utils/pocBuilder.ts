/**
 * POC 表单构建器核心逻辑。
 *
 * 把结构化的「协议 + 请求 + 匹配器」状态生成/解析为 POC 内容文本，
 * 支持 nuclei-yaml 与 json 两种声明式格式；pocsuite3/raw-script 为代码，
 * 不参与结构化构建，仅走源码模式。
 *
 * 生成使用 js-yaml（nuclei）保证输出合法；解析同样走 js-yaml.load，
 * 保证编辑回填的可靠性。构建器状态会随 extra_meta.builder 持久化，
 * 保证编辑时精确回填。
 */

import { dump, load } from 'js-yaml'
import type { AffectedVersion, PocCreatePayload, PocUpdatePayload, Reference } from '@/types/poc'

// ── 协议与字段结构 ───────────────────────────────────────────────

export type Protocol = 'http' | 'tcp' | 'dns' | 'network' | 'websocket'

export interface KeyValue {
  key: string
  value: string
}

export interface HttpSpec {
  method: string
  paths: string[]
  headers: KeyValue[]
  body: string
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
}

export interface NetworkSpec {
  inputs: string[]
  port: string
  data: string
  readBytes: number
  tls: boolean
  tlsSni: string
}

export interface WebSocketSpec {
  url: string
  method: string
  headers: KeyValue[]
  body: string
  readOnce: boolean
}

export interface Matcher {
  id: string
  type: 'word' | 'status' | 'dsl' | 'regex'
  part: 'header' | 'body' | 'all' | ''
  words: string[]
  status: number[]
  condition: 'and' | 'or'
  negative: boolean
}

export interface Extractor {
  id: string
  type: 'regex' | 'dsl' | 'json' | 'kval' | 'xpath'
  name: string
  part: '' | 'header' | 'body' | 'all'
  expressions: string[]
  group: number
  internal: boolean
}

export interface BuilderState {
  protocol: Protocol
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
  { value: 'websocket', label: 'WebSocket', desc: 'WebSocket：URL / 消息 / 请求头 / 响应' },
]

export const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH']
export const DNS_QUERY_TYPES = ['A', 'AAAA', 'NS', 'CNAME', 'TXT', 'MX', 'SOA', 'PTR', 'CAA']
export const MATCHER_TYPES = ['word', 'status', 'dsl', 'regex']
export const MATCHER_PARTS = ['all', 'body', 'header']
export const EXTRACTOR_TYPES = ['regex', 'dsl', 'json', 'kval', 'xpath']
export const EXTRACTOR_PARTS = ['all', 'body', 'header']

let _matcherSeq = 0
export function genMatcherId(): string {
  _matcherSeq += 1
  // 用递增序号 + 计数器构造稳定唯一 id（不依赖 Math.random/Date）
  return `m${_matcherSeq}`
}

export function createEmptyState(): BuilderState {
  return {
    protocol: 'http',
    http: {
      method: 'GET',
      paths: ['{{BaseURL}}'],
      headers: [],
      body: '',
    },
    tcp: { inputs: ['{{Hostname}}'], port: '', data: '', readBytes: 0 },
    dns: { domains: ['{{Hostname}}'], recursion: false, queryType: 'A' },
    network: { inputs: ['{{Hostname}}'], port: '', data: '', readBytes: 0, tls: false, tlsSni: '' },
    websocket: { url: '', method: 'GET', headers: [], body: '', readOnce: false },
    matchers: [
      { id: genMatcherId(), type: 'word', part: 'body', words: ['vulnerable'], status: [], condition: 'or', negative: false },
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
  if (ctx.fofaSyntax) meta.fofa = ctx.fofaSyntax
  if (ctx.shodanSyntax) meta.shodan = ctx.shodanSyntax
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
    if (m.type === 'word' || m.type === 'regex') o.words = m.words.filter((w) => w !== '')
    if (m.type === 'status') o.status = m.status.filter((n) => !Number.isNaN(n))
    if (m.type === 'dsl') o.dsl = m.words.filter((w) => w !== '')
    if (m.type === 'word' || m.type === 'dsl') o.condition = m.condition
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
    return o
  })
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

  if (s.protocol === 'http') {
    const item: Record<string, unknown> = {
      method: s.http.method,
      path: s.http.paths.filter((p) => p !== ''),
    }
    const headers = s.http.headers.filter((kv) => kv.key.trim() !== '')
    if (headers.length) {
      item.headers = Object.fromEntries(headers.map((kv) => [kv.key, kv.value]))
    }
    if (s.http.body.trim()) item.body = s.http.body
    item.matchers = matchers
    if (extractors.length) item.extractors = extractors
    obj.http = [item]
  } else if (s.protocol === 'tcp') {
    const item: Record<string, unknown> = {
      inputs: s.tcp.inputs.filter((i) => i !== ''),
    }
    if (s.tcp.port.trim()) item.port = s.tcp.port
    if (s.tcp.data.trim()) item.data = s.tcp.data
    if (s.tcp.readBytes > 0) item['read-size'] = `${s.tcp.readBytes}b`
    item.matchers = matchers
    if (extractors.length) item.extractors = extractors
    obj.tcp = [item]
  } else if (s.protocol === 'network') {
    const item: Record<string, unknown> = {
      inputs: s.network.inputs.filter((i) => i !== ''),
    }
    if (s.network.port.trim()) item.port = s.network.port
    if (s.network.data.trim()) item.data = s.network.data
    if (s.network.readBytes > 0) item['read-size'] = `${s.network.readBytes}b`
    const netOpts: Record<string, unknown> = {}
    netOpts.tls = s.network.tls
    if (s.network.tlsSni.trim()) netOpts['sni'] = s.network.tlsSni
    item['network'] = netOpts
    item.matchers = matchers
    if (extractors.length) item.extractors = extractors
    obj.network = [item]
  } else if (s.protocol === 'websocket') {
    const item: Record<string, unknown> = {}
    if (s.websocket.url.trim()) item.url = s.websocket.url
    if (s.websocket.method.trim()) item.method = s.websocket.method
    const headers = s.websocket.headers.filter((kv) => kv.key.trim() !== '')
    if (headers.length) {
      item.headers = Object.fromEntries(headers.map((kv) => [kv.key, kv.value]))
    }
    if (s.websocket.body.trim()) item.body = s.websocket.body
    if (s.websocket.readOnce) item['read-once'] = true
    item.matchers = matchers
    if (extractors.length) item.extractors = extractors
    obj.websocket = [item]
  } else {
    // dns
    const item: Record<string, unknown> = { name: '{{FQDN}}' }
    const domains = s.dns.domains.filter((d) => d !== '')
    if (domains.length) item.domains = domains
    if (s.dns.queryType) item.type = s.dns.queryType
    if (s.dns.recursion) item.recursion = true
    item.matchers = matchers
    if (extractors.length) item.extractors = extractors
    obj.dns = [item]
  }
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
  }
  const reference = buildReferenceList(ctx.references)
  if (reference) obj.references = reference
  const metadata = buildMetadata(ctx)
  if (metadata) obj.metadata = metadata
  const extractors = buildExtractors(s.extractors)
  if (extractors.length) obj.extractors = extractors
  if (s.protocol === 'http') {
    obj.request = {
      method: s.http.method,
      path: s.http.paths.filter((p) => p !== ''),
      headers: Object.fromEntries(s.http.headers.filter((kv) => kv.key.trim() !== '').map((kv) => [kv.key, kv.value])),
      ...(s.http.body.trim() ? { body: s.http.body } : {}),
    }
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
      host: s.network.inputs.filter((i) => i !== ''),
      ...(s.network.port.trim() ? { port: s.network.port } : {}),
      ...(s.network.data.trim() ? { data: s.network.data } : {}),
      ...(s.network.readBytes > 0 ? { readSize: s.network.readBytes } : {}),
      tls: s.network.tls,
      ...(s.network.tlsSni.trim() ? { sni: s.network.tlsSni } : {}),
    }
  } else if (s.protocol === 'websocket') {
    obj.request = {
      protocol: 'websocket',
      ...(s.websocket.url.trim() ? { url: s.websocket.url } : {}),
      ...(s.websocket.method.trim() ? { method: s.websocket.method } : {}),
      headers: Object.fromEntries(s.websocket.headers.filter((kv) => kv.key.trim() !== '').map((kv) => [kv.key, kv.value])),
      ...(s.websocket.body.trim() ? { body: s.websocket.body } : {}),
      readOnce: s.websocket.readOnce,
    }
  } else {
    // dns
    obj.request = {
      protocol: 'dns',
      domain: s.dns.domains.filter((d) => d !== ''),
      type: s.dns.queryType,
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
      words: Array.isArray(m.words) ? m.words.map(String) : Array.isArray(m.dsl) ? m.dsl.map(String) : [],
      status: Array.isArray(m.status) ? m.status.map((n) => Number(n)).filter((n) => !Number.isNaN(n)) : [],
      condition: (m.condition as Matcher['condition']) || 'or',
      negative: !!m.negative,
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
    }
  })
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
    state.http.method = String(item.method ?? 'GET')
    state.http.paths = Array.isArray(item.path) ? item.path.map(String) : (item.path ? [String(item.path)] : ['{{BaseURL}}'])
    state.http.headers = item.headers && typeof item.headers === 'object'
      ? Object.entries(item.headers).map(([k, v]) => ({ key: k, value: String(v) }))
      : []
    state.http.body = String(item.body ?? '')
    state.matchers = toMatchers(item.matchers)
    state.extractors = toExtractors(item.extractors)
  } else if (Array.isArray(obj.tcp) && obj.tcp.length) {
    state.protocol = 'tcp'
    const item = obj.tcp[0] as Record<string, unknown>
    state.tcp.inputs = Array.isArray(item.inputs) ? item.inputs.map(String) : (item.host ? [String(item.host)] : ['{{Hostname}}'])
    state.tcp.port = String(item.port ?? '')
    state.tcp.data = String(item.data ?? '')
    const rs = String(item['read-size'] ?? '').replace(/b$/i, '')
    state.tcp.readBytes = parseInt(rs, 10) || 0
    state.matchers = toMatchers(item.matchers)
    state.extractors = toExtractors(item.extractors)
  } else if (Array.isArray(obj.network) && obj.network.length) {
    state.protocol = 'network'
    const item = obj.network[0] as Record<string, unknown>
    state.network.inputs = Array.isArray(item.inputs) ? item.inputs.map(String) : (item.host ? [String(item.host)] : ['{{Hostname}}'])
    state.network.port = String(item.port ?? '')
    state.network.data = String(item.data ?? '')
    const rs = String(item['read-size'] ?? '').replace(/b$/i, '')
    state.network.readBytes = parseInt(rs, 10) || 0
    const net = item.network as Record<string, unknown> | undefined
    state.network.tls = !!net?.tls
    state.network.tlsSni = String(net?.sni ?? '')
    state.matchers = toMatchers(item.matchers)
    state.extractors = toExtractors(item.extractors)
  } else if (Array.isArray(obj.websocket) && obj.websocket.length) {
    state.protocol = 'websocket'
    const item = obj.websocket[0] as Record<string, unknown>
    state.websocket.url = String(item.url ?? '')
    state.websocket.method = String(item.method ?? 'GET')
    state.websocket.headers = item.headers && typeof item.headers === 'object'
      ? Object.entries(item.headers).map(([k, v]) => ({ key: k, value: String(v) }))
      : []
    state.websocket.body = String(item.body ?? '')
    state.websocket.readOnce = !!item['read-once']
    state.matchers = toMatchers(item.matchers)
    state.extractors = toExtractors(item.extractors)
  } else if (Array.isArray(obj.dns) && obj.dns.length) {
    state.protocol = 'dns'
    const item = obj.dns[0] as Record<string, unknown>
    state.dns.domains = Array.isArray(item.domains) ? item.domains.map(String) : ['{{Hostname}}']
    state.dns.queryType = String(item.type ?? 'A')
    state.dns.recursion = !!item.recursion
    state.matchers = toMatchers(item.matchers)
    state.extractors = toExtractors(item.extractors)
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
    state.network.inputs = Array.isArray(req.host) ? req.host : (req.host ? [req.host] : ['{{Hostname}}'])
    state.network.port = String(req.port ?? '')
    state.network.data = String(req.data ?? '')
    state.network.readBytes = Number(req.readSize ?? 0)
    state.network.tls = !!req.tls
    state.network.tlsSni = String(req.sni ?? '')
  } else if (req.protocol === 'websocket') {
    state.protocol = 'websocket'
    state.websocket.url = String(req.url ?? '')
    state.websocket.method = String(req.method ?? 'GET')
    state.websocket.headers = Object.entries(req.headers || {}).map(([k, v]) => ({ key: k, value: String(v) }))
    state.websocket.body = String(req.body ?? '')
    state.websocket.readOnce = !!req.readOnce
  } else if (req.protocol === 'dns') {
    state.protocol = 'dns'
    state.dns.domains = Array.isArray(req.domain) ? req.domain : (req.domain ? [req.domain] : ['{{Hostname}}'])
    state.dns.queryType = String(req.type ?? 'A')
    state.dns.recursion = !!req.recursion
  } else {
    state.protocol = 'http'
    state.http.method = String(req.method ?? 'GET')
    state.http.paths = Array.isArray(req.path) ? req.path : (req.path ? [req.path] : ['{{BaseURL}}'])
    state.http.headers = Object.entries(req.headers || {}).map(([k, v]) => ({ key: k, value: String(v) }))
    state.http.body = String(req.body ?? '')
  }
  state.matchers = toMatchers(obj.matchers)
  state.extractors = toExtractors(obj.extractors)
  if (!state.matchers.length) state.matchers = createEmptyState().matchers
  return state
}

export function parseContent(content: string, format: string): BuilderState {
  if (format === 'json') return parseJson(content)
  return parseNucleiYaml(content)
}

export function canBuild(format: string): boolean {
  return format === 'nuclei-yaml' || format === 'json'
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
